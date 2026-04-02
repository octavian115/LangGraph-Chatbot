from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Annotated
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.graph.message import add_messages
from dotenv import load_dotenv
import sqlite3
from langgraph.checkpoint.postgres import PostgresSaver
import psycopg
import os

load_dotenv()

DB_URI = os.environ.get("DATABASE_URL")

# llm = ChatOpenAI(model="gpt-4o-mini")
llm = ChatGoogleGenerativeAI(model = "gemini-2.5-flash")

class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

def chat_node(state: ChatState):
    messages = state['messages']
    response = llm.invoke(messages)

    return {"messages": [response]}


#create a database
# conn = sqlite3.connect(database='chatbot.db', check_same_thread=False)
connection_kwargs = {"autocommit": True, "prepare_threshold": 0}
conn = psycopg.connect(DB_URI, **connection_kwargs)
# Checkpointer
# checkpointer = SqliteSaver(conn=conn)
checkpointer = PostgresSaver(conn)
checkpointer.setup()  # creates tables on first run

graph = StateGraph(ChatState)
graph.add_node("chat_node", chat_node)

graph.add_edge(START, "chat_node")
graph.add_edge("chat_node", END)

chatbot = graph.compile(checkpointer=checkpointer)


# utility function
def load_conversation(thread_id):
    state = chatbot.get_state(config={'configurable': {'thread_id': thread_id}})

    # to avoid a key error if the thread is empty
    return state.values.get('messages',[])

def retrieve_all_threads():
    all_threads = {}
    for checkpoint in checkpointer.list(None):
        thread_id = checkpoint.config["configurable"]['thread_id']
        if thread_id not in all_threads:
            messages = checkpoint.checkpoint.get("channel_values", {}).get("messages", [])
            first_human = next((m for m in messages if isinstance(m, HumanMessage)), None)
            label = first_human.content[:30] if first_human else str(thread_id)[:8]
            all_threads[thread_id] = label

    return all_threads

def delete_thread(thread_id):
    conn.execute("DELETE FROM checkpoints WHERE thread_id = %s", (str(thread_id),))
    conn.execute("DELETE FROM checkpoint_writes WHERE thread_id = %s", (str(thread_id),))
    conn.execute("DELETE FROM checkpoint_blobs WHERE thread_id = %s", (str(thread_id),))
    conn.commit()

