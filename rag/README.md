# Classic RAG (LangChain + OpenAI Vector Store)

This folder contains a simple, classic RAG example that:
- Ingests the same sample text as the GraphRAG demo
- Splits text into chunks and stores embeddings in an OpenAI Vector Store (via LangChain abstraction)
- Runs a retrieval + generation query with source citations

## Prerequisites
- Python 3.12+
- An OpenAI API key set in `.env` or your shell: `OPENAI_API_KEY=...`

## Install

Use your existing virtualenv (e.g., `dev/`) or create one, then install:

```
pip install -r requirements.txt
```

## Files
- `ingest.py`: builds the vector store from the sample text
- `query.py`: queries the store with a question and returns an answer with citations
- `config.py`: shared config/env helpers

## Quickstart

1) Ingest the sample data into the vector store
```
python rag/ingest.py
```

2) Ask questions
```
python rag/query.py --question "Who is Maria Zielińska?"
```

## Notes
- This uses LangChain, `langchain-openai` for embeddings/LLM, and the OpenAI Vector Store integration.
- By default it creates one vector store named `classic-rag-store` and a single index `docs` under it. You can override via env vars.
- Source chunks and metadata are returned for transparency.
