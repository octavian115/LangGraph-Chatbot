import streamlit as st
from langgraph_tool_backend import chatbot, retrieve_all_threads, delete_thread
from langchain_core.messages import HumanMessage
import uuid
import re

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

st.sidebar.markdown("""
    <p style="font-family: Georgia, serif; font-size: 22px; 
              font-weight: 300; letter-spacing: 0.06em; 
              color: white; margin: 0 0 16px;">
        Narad
    </p>
""", unsafe_allow_html=True)

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

    _, col, _ = st.columns([1, 2, 1])
    with col:
        st.markdown("""
            <div style="padding: 80px 0 40px;">
                <h1 style="font-family: Georgia, serif; font-size: 56px; font-weight: 300; letter-spacing: 0.08em; margin: 0 0 12px; padding: 0; color: white;">
                    Narad
                </h1>
                <p style="font-size: 11px; letter-spacing: 0.2em; text-transform: uppercase; color: gray; margin: 0;">
                    Where ideas take shape
                </p>
            </div>
        """, unsafe_allow_html=True)
else:
    for message in st.session_state['message_history']:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            

# asking user for the input
user_input =st.chat_input("What's on your mind today?")

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
            def ai_only_stream(query):
                for message_chunk, metadata in chatbot.stream(
                    {"messages": [HumanMessage(content=query)]},
                    config=CONFIG,
                    stream_mode="messages"
                ):
                    if metadata.get("langgraph_node") == "chat_node": # filtering for chat node
                        content = message_chunk.content
                        # Gemini returns a list of content blocks
                        if isinstance(content, list):
                            for block in content:
                                if isinstance(block, dict) and block.get("type") == "text":
                                    text = block.get("text", "")
                                    if text: # this is filtering for intermediate calls
                                         # to address gemini streaming artifact(backtics)
                                         yield re.sub(r'(?<!`)`(?!`)', '', text)

                        # OpenAI returns a plain string
                        elif isinstance(content, str) and content:
                            yield content

            ai_message = st.write_stream(ai_only_stream(user_input))
        except Exception as e:
            ai_message = "Sorry, I encountered an error. Please try again."
            st.error(f"Error: {e}")

    st.session_state['message_history'].append({"role":"assistant", "content": ai_message})
    
