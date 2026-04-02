# Narad — AI Chatbot

A conversational AI assistant built with LangGraph and Streamlit, featuring multi-session persistence, real-time streaming, and tool-augmented responses.

## Overview

Most chatbot demos manage memory using simple session variables that reset on refresh. Narad uses LangGraph's checkpointing system to maintain separate conversation threads, each persisted to PostgreSQL — so conversations survive process restarts and work across cloud deployments.

The UI allows users to start new conversations, switch between past sessions, and resume them — with the full message history restored from the graph state.

In addition to that tools like search have been integrated with the chatbot that enhance its capabilities and augment its responses.

## Live Demo

[Try Narad](https://your-render-url.onrender.com)

## Tech Stack

- **LangGraph** — graph-based agent framework for state management, checkpointing, and tool orchestration
- **OpenAI-GPT-4o** — LLM with tool calling support
- **Streamlit** — frontend UI with streaming support
- **PostgreSQL** — cloud persistence via LangGraph's PostgresSaver
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
  - `calculator` — arithmetic operations
  - `search` — real-time web search via Tavily
  - `get_stock_info` — stock prices and financials via yfinance (US and Indian markets)

## Architecture
```
User Input
    ↓
chat_node (Gemini 2.5 Flash)
    ↓
tools_condition
    ├── tool call? → ToolNode → back to chat_node
    └── no tool call? → END
```

## Project Structure
```
narad/
├── app.py                          # Streamlit UI
├── langgraph_tool_backend.py       # LangGraph graph + tools + PostgreSQL checkpointer
├── .env                            # API keys
└── pyproject.toml
```

## Getting Started

**1. Clone the repo**
```bash
git clone https://github.com/your-username/narad.git
cd narad
```

**2. Install dependencies**
```bash
uv sync
```

**3. Set up environment variables**
```bash
cp .env.example .env
# Add the following to .env:
# OPENAI_API_KEY=your_key (optional, if switching back to OpenAI)
# GOOGLE_API_KEY=your_key
# TAVILY_API_KEY=your_key
# DATABASE_URL=your_postgres_connection_string
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
- [x] PostgreSQL persistence for cloud deployment
- [x] Deploy on Render with managed Postgres
- [x] Tool-augmented responses (calculator, search, stock info)
- [ ] Upgrade calculator to expression-based eval
- [ ] Add system prompt / persona configuration
- [ ] Multi-agent architecture

