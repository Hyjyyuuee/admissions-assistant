# Admissions Assistant

An AI-powered admissions question-answering system built with a WeChat Mini Program, FastAPI, DeepSeek, SQLite, and a hybrid RAG pipeline.

The application supports multi-turn conversations, persistent chat history, source citations, query routing, entity extraction, knowledge-tool selection, and retrieval tracing.

> The Markdown files under `knowledge/` contain demonstration data only. They do not represent the official policies of any real institution.

## Key Features

- WeChat Mini Program chat interface with conversation history
- FastAPI REST API with SQLite, SQLAlchemy, and Alembic migrations
- Multi-turn context management and persistent conversations
- Markdown document loading and chunking with source, title, and category metadata
- Hybrid retrieval using BM25, BGE embeddings, and a lightweight knowledge graph
- Reciprocal Rank Fusion (RRF) for final result ranking
- Query routing across admissions, faculty, and policy knowledge domains
- Entity extraction and automatic knowledge-tool selection
- DeepSeek-powered answer generation with source citations
- Local fallback responses when the LLM service is unavailable
- Retrieval logs and an interactive Retrieval Trace interface

## Architecture

```text
WeChat Mini Program
        |
        v
FastAPI REST API
        |
        +-- Conversation and history management
        +-- Query router and entity extraction
        +-- Knowledge-tool selection
        |
        v
BM25 + BGE Embeddings + Knowledge Graph
        |
        v
Reciprocal Rank Fusion
        |
        v
DeepSeek / Local Fallback
        |
        v
Answer + Sources + Retrieval Logs
```

## Technology Stack

- **Frontend:** WeChat Mini Program, JavaScript, WXML, WXSS
- **Backend:** Python, FastAPI, Pydantic
- **Database:** SQLite, SQLAlchemy, Alembic
- **LLM:** DeepSeek API
- **Retrieval:** BM25, FastEmbed, `BAAI/bge-small-zh-v1.5`
- **RAG:** Hybrid retrieval, RRF, lightweight Graph RAG

## Project Structure

```text
backend/       FastAPI application, database, retrieval, routing, and LLM logic
alembic/       Database migrations
knowledge/     Demonstration Markdown knowledge base
data/          Runtime data and the legacy JSON example
miniprogram/   WeChat Mini Program frontend
```

## Windows Quick Start

### Prerequisites

- Python 3.11 or 3.12
- WeChat Developer Tools

Make sure **Add Python to PATH** is selected during Python installation.

### Start the backend

Double-click `start-backend.bat` in Windows File Explorer, or run the following command in the VS Code terminal:

```powershell
.\start-backend.bat
```

The first startup creates a virtual environment, installs dependencies, applies database migrations, and loads the demonstration knowledge base.

After startup, open:

- Swagger API documentation: `http://127.0.0.1:8001/docs`
- Health check: `http://127.0.0.1:8001/api/health`
- Retrieval Trace: `http://127.0.0.1:8001/debug/retrieval`

### Start the Mini Program

1. Open WeChat Developer Tools.
2. Import the `miniprogram` directory.
3. Disable domain validation for local development.
4. For testing on a physical device, update the API address in `miniprogram/app.js` to the computer's LAN IP address.

## Configuration

Copy `.env.example` to `.env` if the startup script has not created it automatically. Then configure the DeepSeek API key:

```env
DEEPSEEK_API_KEY=your_api_key
```

The application remains usable without an API key and returns locally generated answers based on retrieved content.

For production deployment, configure:

```env
APP_ENV=production
ENABLE_DEBUG_ENDPOINTS=false
MINIPROGRAM_ORIGIN=https://your-allowed-origin.example
```

Never commit the real `.env` file or API credentials.

## Hybrid Retrieval

Documents are loaded from `knowledge/` and divided into chunks based on Markdown headings and paragraphs. Each chunk retains its source path, title, and category.

The retrieval pipeline combines:

1. **BM25** for keyword and domain-term matching
2. **BGE embeddings** for semantic similarity
3. **Lightweight Graph RAG** for entity-to-document relationships
4. **RRF** to merge the three ranked result lists

The default fusion weights are BM25 0.50, BGE 0.35, and Graph 0.15. Embeddings are cached under `data/` and rebuilt automatically when the model or document content changes.

## Routing and Knowledge Tools

The soft query router identifies whether a question primarily concerns `admissions`, `faculty`, or `policy`. It then selects one or more domain tools:

- `admissions_kb`
- `faculty_kb`
- `policy_kb`

Routing adds a ranking preference without blocking relevant cross-domain results. Entity extraction also normalizes concepts such as application materials, application status, scholarships, tuition, international students, and academic programs.

## Retrieval Trace

The Retrieval Trace page explains how an answer is retrieved. It displays:

- The selected route and knowledge tools
- Extracted entities and the enhanced query
- BM25, BGE, graph, and final ranking scores
- Knowledge-graph relationships
- Recent retrieval logs

The trace endpoint performs retrieval only and does not call DeepSeek.

## Validation

Run the retrieval regression tests:

```powershell
.\evaluate-retrieval.bat
```

Run the API smoke tests while the backend is active:

```powershell
.\smoke-tests.bat
```

The current fixed test suite passes 6/6 retrieval cases and 4/4 core API smoke checks.

## Disclaimer

This repository is intended for technical demonstration and portfolio purposes. All institution-related knowledge is generic demonstration content. Always consult the relevant institution's official website or admissions office for authoritative information.

