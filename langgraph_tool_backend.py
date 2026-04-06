from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Annotated
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.graph.message import add_messages
from dotenv import load_dotenv
import sqlite3
from langgraph.checkpoint.postgres import PostgresSaver
import psycopg
import os
import requests
from datetime import datetime
import tempfile
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings

# for tools
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.tools import tool
import yfinance as yf
from tavily import TavilyClient

load_dotenv()

DB_URI = os.environ.get("DATABASE_URL")

# ------------------------------------ LLM ----------------------------------------

llm = ChatOpenAI(model="gpt-4o")
# llm = ChatGoogleGenerativeAI(model = "gemini-2.5-flash")

# ---------------------------------- RAG SETUP --------------------------------------

embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

# per-thread retriever store
_THREAD_RETRIEVERS = {}
_THREAD_METADATA = {}

def ingest_pdf(file_bytes: bytes, thread_id: str, filename: str = None) -> dict:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name

    try:
        docs = PyPDFLoader(tmp_path).load()
        chunks = RecursiveCharacterTextSplitter(
            chunk_size=1000, chunk_overlap=200
        ).split_documents(docs)

        vector_store = FAISS.from_documents(chunks, embeddings)
        retriever = vector_store.as_retriever(
            search_type="similarity", search_kwargs={"k": 4}
        )

        _THREAD_RETRIEVERS[str(thread_id)] = retriever
        _THREAD_METADATA[str(thread_id)] = {
            "filename": filename,
            "pages": len(docs),
            "chunks": len(chunks),
        }

        return _THREAD_METADATA[str(thread_id)]
    finally:
        os.remove(tmp_path)

# ------------------------------------ TOOLS ---------------------------------------

# Tool 1
@tool
def calculator(expression: str) -> dict:
    """
    Evaluate a mathematical expression.
    Supports: +, -, *, /, **, %, parentheses.
    Examples: '3 + 4 * 2', '(10 / 2) + 5', '2 ** 8'
    """
    try:
        allowed_names = {"abs": abs, "round": round, "min": min, "max": max}
        result = eval(expression, {"__builtins__": {}}, allowed_names)
        return {"expression": expression, "result": result}
    except ZeroDivisionError:
        return {"error": "Division by zero"}
    except Exception as e:
        return {"error": f"Invalid expression: {str(e)}"}
    
# Tool 2
@tool
def search(query: str) -> dict:
    """
    Search the web for current information.
    Use this for recent events, news, or anything that requires up-to-date knowledge.
    """
    try:
        client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
        # days parameter to priortize recent results
        response = client.search(query, max_results=3, search_depth="advanced",days=7)
        return {
            "query": query,
            "results": [
                {"title": r["title"], "url": r["url"], "content": r["content"]}
                for r in response["results"]
            ]
        }
    except Exception as e:
        return {"error": str(e)}
    
# Tool 3
@tool
def get_stock_info(ticker: str) -> dict:
    """
    Get current stock information for a given ticker symbol.
    Use this when the user asks about a stock price or company financials.
    

    For US stocks, use the ticker directly. Examples: 'AAPL', 'TSLA', 'GOOGL'
    For Indian stocks listed on NSE, append '.NS'. Examples: 'ZOMATO.NS', 'RELIANCE.NS', 'INFY.NS', 'TCS.NS'
    For Indian stocks listed on BSE, append '.BO'. Examples: 'RELIANCE.BO'
    When in doubt for Indian stocks, prefer the .NS suffix.
    """
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        return {
            "ticker": ticker.upper(),
            "name": info.get("longName"),
            "price": info.get("currentPrice"),
            "currency": info.get("currency"),
            "market_cap": info.get("marketCap"),
            "pe_ratio": info.get("trailingPE"),
            "52_week_high": info.get("fiftyTwoWeekHigh"),
            "52_week_low": info.get("fiftyTwoWeekLow"),
        }
    except Exception as e:
        return {"error": str(e)}
    
# Tool 4 - RAG (dynamic, per-thread)
def make_rag_tool(thread_id: str):
    retriever = _THREAD_RETRIEVERS.get(str(thread_id))

    @tool
    def rag_tool(query: str) -> dict:
        """
        Retrieve relevant information from the uploaded PDF document.
        Use this when the user asks questions about their uploaded document.
        """
        if retriever is None:
            return {"error": "No PDF uploaded for this session. Please upload a PDF first."}

        results = retriever.invoke(query)
        context = [doc.page_content for doc in results]
        metadata = [doc.metadata for doc in results]

        return {
            "query": query,
            "context": context,
            "metadata": metadata,
            "source": _THREAD_METADATA.get(str(thread_id), {}).get("filename"),
        }

    return rag_tool

# # make a tool list
# tools = [calculator,search,get_stock_info]

# # tool binding
# llm_with_tools = llm.bind_tools(tools)



# ------------------------------------ STATE --------------------------------------- 

class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


# ------------------------------------ NODES --------------------------------------- 

# base tools (always available)
base_tools = [calculator, search, get_stock_info]

def get_tools_for_thread(thread_id: str):
    tools = base_tools.copy()
    if str(thread_id) in _THREAD_RETRIEVERS:
        tools.append(make_rag_tool(thread_id))
    return tools


def chat_node(state: ChatState, config):
    thread_id = config["configurable"]["thread_id"]
    tools = get_tools_for_thread(thread_id)

    system_prompt = SystemMessage(content=f"""You are Narad, a helpful AI assistant.
    Today's date is {datetime.now().strftime("%B %d, %Y")}.
    You have access to the following tools:
    - search: use for current events, news, or anything time-sensitive
    - get_stock_info: use for stock prices and company financials
    - calculator: use for arithmetic operations
    {"- rag_tool: use for answering questions about the uploaded PDF document. If the document doesn't contain the answer, fall back to other tools like search." if len(tools) > 3 else ""}

    Always use the search tool for recent events or news. Never answer time-sensitive questions from memory.
    If the user asks about their uploaded document, always use the rag_tool first.
    If the rag_tool returns no relevant information, DO NOT give up — use the search tool to find the answer from the web instead.
    """)

    messages = [system_prompt] + state['messages']
    response = llm.bind_tools(tools).invoke(messages)

    return {"messages": [response]}

def tool_node(state: ChatState, config):
    thread_id = config["configurable"]["thread_id"]
    tools = get_tools_for_thread(thread_id)
    return ToolNode(tools).invoke(state)


# ------------------------------------ CHECKPOINTER -------------------------------------

#create a database
# conn = sqlite3.connect(database='chatbot.db', check_same_thread=False)

connection_kwargs = {"autocommit": True, "prepare_threshold": 0}
conn = psycopg.connect(DB_URI, **connection_kwargs)

# Checkpointer
# checkpointer = SqliteSaver(conn=conn)

checkpointer = PostgresSaver(conn)
checkpointer.setup()  # creates tables on first run


# ------------------------------------ GRAPH ------------------------------------------- 

graph = StateGraph(ChatState)
graph.add_node("chat_node", chat_node)
graph.add_node("tools", tool_node)

graph.add_edge(START, "chat_node")
graph.add_conditional_edges("chat_node", tools_condition)
graph.add_edge('tools', 'chat_node')

chatbot = graph.compile(checkpointer=checkpointer)



# ------------------------------------ UTILITY FUNCTIONS ---------------------------------

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
