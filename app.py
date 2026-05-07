import streamlit as st
from langgraph_tool_backend import chatbot, retrieve_all_threads, delete_thread
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
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


# to retrieve the chat from database on app restart
try:
    if 'chat_threads' not in st.session_state:
        with st.spinner("Waking up the database... (free tier cold start, takes a few seconds)"):
            st.session_state['chat_threads'] = retrieve_all_threads()
except Exception as e:
    st.error(f"Error: {e}")
    st.stop()

# add the current thread to chat_threads
add_thread(st.session_state['thread_id'])

# checking if user started the chat
if 'chat_started' not in st.session_state:
    st.session_state['chat_started'] = False

if "thread_files" not in st.session_state:
    st.session_state["thread_files"] = {}

if 'pending_prompt' not in st.session_state:
    st.session_state['pending_prompt'] = None

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
            elif isinstance(msg, AIMessage) and msg.content:
                role = 'assistant'
            else:
                continue # skips tool message and empty AI messages (tool call decisions)
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

# ********************************* PDF Upload **************************************

uploaded_pdf = st.sidebar.file_uploader(
    "Upload a PDF",
    type=["pdf"],
    key=f"pdf_uploader_{st.session_state['thread_id']}"
)

current_thread = str(st.session_state['thread_id'])

# show indicator if this thread has an indexed PDF
if current_thread in st.session_state.get("thread_files", {}):
    st.sidebar.info(f"📄 {st.session_state['thread_files'][current_thread]}")

if uploaded_pdf:
    current_thread = str(st.session_state['thread_id'])
    # only ingest if this is a new file
    if st.session_state["thread_files"].get(current_thread) != uploaded_pdf.name:
        with st.spinner(f"Indexing {uploaded_pdf.name}..."):
            from langgraph_tool_backend import ingest_pdf
            result = ingest_pdf(
                file_bytes=uploaded_pdf.read(),
                thread_id=current_thread,
                filename=uploaded_pdf.name,
            )
        st.session_state["thread_files"][current_thread] = uploaded_pdf.name
        st.sidebar.success(f"Indexed: {result['pages']} pages, {result['chunks']} chunks")

# ************************************ Main UI **************************************

user_input = None
if st.session_state.get('pending_prompt'):
    user_input = st.session_state['pending_prompt']
    st.session_state['pending_prompt'] = None
    st.session_state['chat_started'] = True

# welcome screen when no messages and when users starts the chat
if not st.session_state['chat_started'] and len(st.session_state['message_history']) == 0:

    _, col, _ = st.columns([1, 2, 1])
    with col:
        st.markdown("""
            <div style="padding: 80px 0 40px;">
                <h1 style="font-family: Georgia, serif; font-size: 56px; font-weight: 300; letter-spacing: 0.08em; margin: 0 0 12px; padding: 0; color: white;">
                    Narad
                </h1>
                <p style="font-size: 11px; letter-spacing: 0.2em; text-transform: uppercase; color: gray; margin: 0 0 32px;">
                    Web search · Stocks · Math · PDF Q&A
                </p>
            </div>
        """, unsafe_allow_html=True)

        # example prompt chips
        examples = [
            ("📈", "What's Zomato trading at?"),
            ("🔍", "Latest news on AI agents"),
            ("🧮", "Calculate 15% tip on ₹2,847"),
            ("📄", "Upload a PDF in the sidebar to ask questions"),
        ]
        c1, c2 = st.columns(2)
        for i, (emoji, prompt) in enumerate(examples):
            target = c1 if i % 2 == 0 else c2
            if target.button(f"{emoji}  {prompt}", key=f"example_{i}", use_container_width=True):
                if not prompt.startswith("Upload"):  # last one is informational, not clickable
                    st.session_state['pending_prompt'] = prompt
                    st.rerun()
else:
    for message in st.session_state['message_history']:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            

# asking user for the input — fall through to chat_input only if no pending prompt
if user_input is None:
    user_input = st.chat_input("What's on your mind today?")

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

    
    status_placeholder = st.empty()

    with st.chat_message("assistant"):

        CONFIG = {
            "configurable": {'thread_id': st.session_state['thread_id']},
            "metadata": {
                "thread_id": st.session_state['thread_id']
            },
            "run_name": "chat_turn",
        }

        try:
            status_holder = {"box": None}
            thinking_box = st.empty()
            thinking_box.markdown("_Thinking..._")
            first_chunk_received = {"flag": False}


            def ai_only_stream(query):
                def dismiss_thinking():
                    if not first_chunk_received["flag"]:
                        thinking_box.empty()
                        first_chunk_received["flag"] = True

                for message_chunk, metadata in chatbot.stream(
                    {"messages": [HumanMessage(content=query)]},
                    config=CONFIG,
                    stream_mode="messages"
                ):
                    if isinstance(message_chunk, ToolMessage):
                        dismiss_thinking()
                        tool_name = getattr(message_chunk, "name", "tool")
                        status_holder["last_tool"] = tool_name 
                        with status_placeholder:
                            if status_holder["box"] is None:
                                status_holder["box"] = st.status(
                                    f"🔧 Using `{tool_name}`…", expanded=True
                                )
                            else:
                                status_holder["box"].update(
                                    label=f"🔧 Using `{tool_name}`…",
                                    state="running",
                                    expanded=True,
                                )

                    if metadata.get("langgraph_node") == "chat_node":
                        content = message_chunk.content
                        if isinstance(content, list):
                            for block in content:
                                if isinstance(block, dict) and block.get("type") == "text":
                                    text = block.get("text", "")
                                    if text:
                                        dismiss_thinking()
                                        yield re.sub(r'(?<!`)`(?!`)', '', text)
                        elif isinstance(content, str) and content:
                            dismiss_thinking()
                            yield re.sub(r'(?<!`)`(?!`)', '', content)

            ai_message = st.write_stream(ai_only_stream(user_input))

            if status_holder["box"] is not None:
                last_tool = status_holder.get("last_tool", "tool")
                status_holder["box"].update(
                    label=f"Used `{last_tool}`", state="complete", expanded=False
                )

        except Exception as e:
            ai_message = "Sorry, I encountered an error. Please try again."
            st.error(f"Error: {e}")

    st.session_state['message_history'].append({"role":"assistant", "content": ai_message})