# Narad — AI Chatbot

A conversational AI assistant built with LangGraph and Streamlit, featuring multi-session persistence, real-time streaming, and tool-augmented responses including document-grounded Q&A.

## Overview

Most chatbot demos manage memory using simple session variables that reset on refresh. Narad uses LangGraph's checkpointing system to maintain separate conversation threads, each persisted to PostgreSQL — so conversations survive process restarts and work across cloud deployments.

The UI allows users to start new conversations, switch between past sessions, and resume them — with the full message history restored from the graph state.

The agent dynamically selects from multiple tools — web search, stock lookup, calculator, and a RAG pipeline — based on the user's query. When a PDF is uploaded, the agent can retrieve relevant context from it alongside using other tools in the same turn.

## Live Demo

[Try Narad](https://narad-chat.onrender.com)

## Tech Stack

- **LangGraph** — graph-based agent framework for state management, checkpointing, and tool orchestration
- **OpenAI GPT-4o** — LLM with tool calling support
- **Streamlit** — frontend UI with streaming support
- **PostgreSQL** — cloud persistence via LangGraph's PostgresSaver
- **FAISS** — in-memory vector store for per-session document retrieval
- **OpenAI Embeddings** — text-embedding-3-small for document chunking
- **LangSmith** — observability and trace monitoring per conversation thread
- **Python 3.11 / uv** — runtime and package management

## Features

- Multi-session chat with thread-based isolation
- Streaming responses via `st.write_stream`
- PostgreSQL persistence — conversations survive app restarts and deployments
- Conversation history restored from LangGraph state on session switch
- Sidebar navigation with auto-labeled chat threads
- LangSmith tracing organized by thread ID
- **Tool-augmented responses:**
  - `calculator` — solves arithmetic expressions
  - `search` — real-time web search via Tavily
  - `get_stock_info` — stock prices and financials via yFinance (US and Indian markets)
  - `rag_tool` — document Q&A over user-uploaded PDFs using FAISS retrieval
- **Agentic RAG:**
  - Upload a PDF per session — automatically chunked, embedded, and indexed
  - Agent decides when to use document retrieval vs. other tools
  - Supports multi-tool queries in a single turn (e.g., RAG + web search)
  - Dynamic tool binding via closures — RAG tool is scoped per thread without passing internal IDs to the LLM

## Architecture
```
User Input
    ↓
chat_node (GPT-4o + dynamic tool binding)
    ↓
tools_condition
    ├── tool call? → ToolNode → back to chat_node
    └── no tool call? → END
```

**RAG Pipeline:**
```
PDF Upload → PyPDFLoader → RecursiveCharacterTextSplitter → OpenAI Embeddings → FAISS
    ↓
rag_tool (closure-bound per thread) → retriever.invoke(query) → context returned to LLM
```

## Project Structure
```
narad/
├── streamlit_frontend_database.py  # Streamlit UI with PDF upload and streaming
├── langgraph_tool_backend.py       # LangGraph graph + tools + RAG + PostgreSQL checkpointer
├── .env                            # API keys
└── pyproject.toml
```

## Getting Started

**1. Clone the repo**
```bash
git clone https://github.com/octavian115/LangGraph-Chatbot.git
cd LangGraph-Chatbot
```

**2. Install dependencies**
```bash
uv sync
```

**3. Set up environment variables**
```bash
cp .env.example .env
# Add the following to .env:
# OPENAI_API_KEY=your_key
# TAVILY_API_KEY=your_key
# DATABASE_URL=your_postgres_connection_string
# LANGCHAIN_TRACING_V2=true
# LANGCHAIN_API_KEY=your_langsmith_key
```

**4. Run the app**
```bash
streamlit run streamlit_frontend_database.py
```

## Roadmap

- [x] In-memory persistence via MemorySaver
- [x] SQLite persistence across restarts
- [x] LangSmith observability
- [x] PostgreSQL persistence for cloud deployment
- [x] Deploy on Render with managed Postgres
- [x] Tool-augmented responses (calculator, search, stock info)
- [x] Agentic RAG — PDF upload with per-session FAISS retrieval
- [ ] Human-in-the-loop (HITL) 