import streamlit as st
from langgraph_database_backend import chatbot, retrieve_all_threads, delete_thread
from langchain_core.messages import HumanMessage
import uuid

st.markdown("""
    <style>
    [data-testid="stSidebarContent"] .stButton button {
        height: 50px;
    }
    </style>
""", unsafe_allow_html=True)

# ******************************** Utility Functions *************************************

def generate_thread_id():
    thread_id = uuid.uuid4()
    return thread_id

def reset_chat():
    thread_id = generate_thread_id()
    st.session_state['thread_id'] = thread_id
    add_thread(st.session_state['thread_id'])
    st.session_state['message_history'] = []
    st.session_state['chat_started'] = False
    st.rerun()

def add_thread(thread_id):
    if thread_id not in st.session_state['chat_threads']:
        st.session_state['chat_threads'][thread_id] = str(thread_id)[:8]

def load_conversation(thread_id):
    try:
        state = chatbot.get_state(config={'configurable': {'thread_id': thread_id}})

        # to avoid a key error if the thread is empty
        return state.values.get('messages',[])
    except Exception as e:
        st.error(f"Failed to load conversation: {e}")
        # returning an empty list so that the app still shows sidebar. with no messgaes
        return []

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

# checking if user started the chat
if 'chat_started' not in st.session_state:
    st.session_state['chat_started'] = False

# ********************************* Sidebar UI **************************************

st.sidebar.title("LangGraph Chatbot")

if st.sidebar.button("New Chat"):
    reset_chat()

st.sidebar.header("Chat History")

# displaying all the chat threads in the sidebar
for thread_id, label in reversed(st.session_state['chat_threads'].items()):
    col1,col2 = st.sidebar.columns([4,1])
    if col1.button(label, key=str(thread_id), use_container_width=True):

        st.session_state['thread_id'] = thread_id
        st.session_state['chat_started'] = True  # it has messages

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
    
    if col2.button("🗑", key=f"del_{thread_id}", use_container_width=True):

        delete_thread(thread_id) # remove from DB

        del st.session_state['chat_threads'][thread_id] # remove from UI
        
        if st.session_state['thread_id'] == thread_id:
            # where user deletes the current thread
            reset_chat()
        else:
            st.rerun()

# ************************************ Main UI **************************************

# welcome screen when no messages and when users starts the chat
if not st.session_state['chat_started'] and len(st.session_state['message_history']) == 0:

    st.markdown("""
            <div style="display: flex; flex-direction: column; align-items: center; 
                    justify-content: center; padding: 80px 20px 40px;">
            <h1 style="font-size: 26px; font-weight: 500; margin-bottom: 8px;">
                LangGraph Chatbot
            </h1>
            <p style="color: gray; font-size: 15px;">
                Your conversations are saved and can be resumed anytime.
            </p>
        </div>
    """, unsafe_allow_html=True)
else:
    for message in st.session_state['message_history']:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])


# asking user for the input
user_input =st.chat_input("Type here...")

if user_input:

    # updating when started chatting
    st.session_state['chat_started'] = True

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

        try:
            ai_message = st.write_stream(
                message_chunk.content for message_chunk, metadata in chatbot.stream(
                    {'messages': [HumanMessage(content=user_input)]},
                    config= CONFIG,
                    stream_mode="messages"
                )
            )
        except Exception as e:
            ai_message = "Sorry, I encountered an error. Please try again."
            st.error(f"Error: {e}")

    st.session_state['message_history'].append({"role":"assistant", "content": ai_message})
    
