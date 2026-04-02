# LangGraph Chatbot

A conversational chatbot built with LangGraph and Streamlit, demonstrating stateful multi-session chat with streaming responses and SQLite persistence.

## Overview

Most chatbot demos manage memory using simple session variables that reset on refresh. This project uses LangGraph's checkpointing system to maintain separate conversation threads, each persisted to a SQLite database — so conversations survive process restarts.

The UI allows users to start new conversations, switch between past sessions, and resume them — with the full message history restored from the graph state.

## Tech Stack

- **LangGraph** — graph-based agent framework for managing conversation state and checkpointing
- **LangChain + OpenAI** — LLM integration (gpt-4o-mini)
- **Streamlit** — frontend UI with streaming support
- **SQLite** — local persistence via LangGraph's SqliteSaver
- **LangSmith** — observability and trace monitoring per conversation thread
- **Python 3.11 / uv** — runtime and package management

## Features

- Multi-session chat with thread-based isolation
- Streaming responses via `st.write_stream`
- SQLite persistence — conversations survive app restarts
- Conversation history restored from LangGraph state on session switch
- Sidebar navigation with auto-labeled chat threads
- LangSmith tracing organized by thread ID

## Project Structure
```
langgraph-chatbot/
├── app.py                          # Streamlit UI
├── langgraph_database_backend.py   # LangGraph graph + SQLite checkpointer
├── .env                            # API keys (not committed)
└── pyproject.toml
```

## Getting Started

**1. Clone the repo**
```bash
git clone https://github.com/your-username/langgraph-chatbot.git
cd langgraph-chatbot
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
# LANGCHAIN_TRACING_V2=true
# LANGCHAIN_API_KEY=your_langsmith_key
```

**4. Run the app**
```bash
streamlit run app.py
```

## Roadmap

- [x] In-memory persistence via MemorySaver
- [x] SQLite persistence across restarts
- [x] LangSmith observability
- [ ] Replace SQLite with PostgreSQL for cloud deployment
- [ ] Deploy on Render with managed Postgres

