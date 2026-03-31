# LangGraph Chatbot

A conversational chatbot built with LangGraph and Streamlit, demonstrating stateful multi-session chat with streaming responses.

## Overview

Most chatbot demos manage memory using simple session variables that reset on refresh. This project uses LangGraph's checkpointing system to maintain separate conversation threads, each with its own persistent state managed by the graph.

The UI allows users to start new conversations, switch between past sessions, and resume them — with the full message history restored from the graph state.

## Tech Stack

- **LangGraph** — graph-based agent framework for managing conversation state
- **LangChain + OpenAI** — LLM integration (gpt-3.5-turbo)
- **Streamlit** — frontend UI with streaming support
- **Python 3.11 / uv** — runtime and package management

## Features

- Multi-session chat with thread-based isolation
- Streaming responses via `st.write_stream`
- Conversation history restored from LangGraph state on session switch
- Sidebar navigation with auto-labeled chat threads

## Project Structure

```
langgraph-chatbot/
├── chatbot.py        # LangGraph graph definition and compilation
├── database.py       # Checkpointer setup
├── app.py            # Streamlit UI
├── .env              # API keys (not committed)
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
# Add your OPENAI_API_KEY to .env
```

**4. Run the app**
```bash
streamlit run app.py
```

## Roadmap

- [ ] Replace `MemorySaver` with PostgreSQL checkpointer for true persistence across restarts
- [ ] Deploy on Render with managed Postgres
- [ ] Add system prompt customization per session