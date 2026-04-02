import streamlit as st
from langgraph_database_backend import chatbot, retrieve_all_threads
from langchain_core.messages import HumanMessage
import uuid
import traceback


# ******************************** Utility Functions *************************************

def generate_thread_id():
    thread_id = uuid.uuid4()
    return thread_id

def reset_chat():
    thread_id = generate_thread_id()
    st.session_state['thread_id'] = thread_id
    add_thread(st.session_state['thread_id'])
    st.session_state['message_history'] = []

def add_thread(thread_id):
    if thread_id not in st.session_state['chat_threads']:
        st.session_state['chat_threads'][thread_id] = str(thread_id)[:8]

def load_conversation(thread_id):
    state = chatbot.get_state(config={'configurable': {'thread_id': thread_id}})

    # to avoid a key error if the thread is empty
    return state.values.get('messages',[])

# ********************************* Session Setup **************************************

if 'message_history' not in st.session_state:
    st.session_state['message_history'] = []

# generating a thread_id and adding it to session
if 'thread_id' not in st.session_state:
    st.session_state['thread_id'] = generate_thread_id()


# to retrieve the chat from database
try:
    if 'chat_threads' not in st.session_state:
        st.session_state['chat_threads'] = retrieve_all_threads()
except Exception as e:
    st.error(f"Error: {e}")
    st.stop()

# add the current thread to chat_threads
add_thread(st.session_state['thread_id'])

# ********************************* Sidebar UI **************************************

st.sidebar.title("LangGraph Chatbot")

if st.sidebar.button("New Chat"):
    reset_chat()

st.sidebar.header("Chat History")

# displaying all the chat threads in the sidebar
for thread_id, label in reversed(st.session_state['chat_threads'].items()):
    if st.sidebar.button(label, key=str(thread_id)):

        st.session_state['thread_id'] = thread_id
        # loading messages for this thread
        messages = load_conversation(thread_id)

        temp_messages = []
        for msg in messages:
            if isinstance(msg, HumanMessage):
                role = 'user'
            else:
                role = 'assistant'
            temp_messages.append({'role':role, 'content': msg.content})
        
        st.session_state['message_history'] = temp_messages

# ************************************ Main UI **************************************

# loading the conversation history
for message in st.session_state['message_history']:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# asking user for the input
user_input =st.chat_input("Type here...")

if user_input:

    # checking if this message is the first one in this thread to display in sidebar
    if len(st.session_state['message_history']) == 0:
        #store the label
        st.session_state['chat_threads'][st.session_state['thread_id']] = user_input

    # first add the message to message_history
    st.session_state['message_history'].append({"role":"user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # generating llm response
    with st.chat_message("assistant"):

        # defining config for the chatbot
        # CONFIG = {'configurable': {'thread_id': st.session_state['thread_id'] }
        # new config to categorize traces in langsmith 
        CONFIG = {
            "configurable": {'thread_id': st.session_state['thread_id']},
            "metadata": {
                "thread_id": st.session_state['thread_id']
            },
            "run_name": "chat_turn",
        }

        ai_message = st.write_stream(
            message_chunk.content for message_chunk, metadata in chatbot.stream(
                {'messages': [HumanMessage(content=user_input)]},
                config= CONFIG,
                stream_mode="messages"
            )
        )

    st.session_state['message_history'].append({"role":"assistant", "content": ai_message})
    
