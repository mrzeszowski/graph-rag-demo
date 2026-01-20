# Graph RAG demo (Neo4j GraphRAG + classic RAG)

This repo contains a small, self-contained demo that compares:

- **GraphRAG**: builds a knowledge graph in **Neo4j**, adds a vector index over `:Chunk` nodes, and answers questions using **graph-augmented retrieval**.
- **Classic RAG**: chunks the same documents and uploads them into an **OpenAI Vector Store**, then answers questions using the OpenAI **Responses API** + `file_search` tool.

The sample documents live in the [data/](data/) folder (a set of ADR-style markdown files).

---

## Prerequisites

- **Python**: 3.12+ recommended
- **Docker**: for running Neo4j locally
- **OpenAI API key**: required for embeddings + LLM calls

---

## Quickstart

### 1) Start Neo4j (Docker)

```bash
docker compose up -d
```

Neo4j will be available at:

- Browser UI: `http://localhost:7474`
- Bolt: `neo4j://localhost:7687`

Default credentials from [docker-compose.yml](docker-compose.yml):

- user: `neo4j`
- password: `password`
- database: `graph.rag.demo`

> If you change the password in `docker-compose.yml`, also update `NEO4J_PASS` in your `.env`.

### 2) Create a virtualenv and install dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3) Configure environment variables

Create a `.env` file in the repo root:

```bash
cp .env.example .env
```

Then edit `.env` and set at least:

- `OPENAI_API_KEY`
- `NEO4J_PASS`

### 4) Build everything (GraphRAG + classic RAG)

This clears Neo4j, rebuilds the knowledge graph, creates/populates the Neo4j vector index, and ingests the same documents into the OpenAI Vector Store.

```bash
zsh rebuild.sh
```

### 5) Run the demo questions

Runs the same set of questions through both pipelines (`graph_rag/query.py` and `rag/query.py`) and writes results into a single session file under [run_results/](run_results/).

```bash
zsh run.sh
```

---

## How it works

### GraphRAG path

- Build KG: [graph_rag/builder.py](graph_rag/builder.py)
- Create Neo4j vector index: [graph_rag/create_vector_index.py](graph_rag/create_vector_index.py)
- Populate embeddings for `:Chunk` nodes: [graph_rag/populate_vector_index.py](graph_rag/populate_vector_index.py)
- Query: [graph_rag/query.py](graph_rag/query.py)

GraphRAG retrieval uses:

- **Vector search** over `:Chunk` nodes
- A small **neighborhood expansion** in Cypher to pull “graph facts” adjacent to each chunk

### Classic RAG path

- Ingest OpenAI Vector Store: [rag/ingest.py](rag/ingest.py)
- Query: [rag/query.py](rag/query.py)

---

## Common commands

### Run only Classic RAG

```bash
python3 rag/ingest.py
python3 rag/query.py --question "Timeline of messaging platform decisions?"
```

### Run only GraphRAG

```bash
python3 graph_rag/cleanup.py
python3 graph_rag/builder.py
python3 graph_rag/create_vector_index.py
python3 graph_rag/populate_vector_index.py
python3 graph_rag/query.py --question "Timeline of messaging platform decisions?"
```

### Verify the Neo4j vector index

```bash
python3 graph_rag/verify_vector_index.py --question "What is this document about?" --top-k 5
```

### Explore the KG in Neo4j Browser

Open `http://localhost:7474` and run:

```cypher
MATCH (n)
OPTIONAL MATCH (n)-[r]->(m)
RETURN n, r, m;
```

(Also available as [get_kg.cypher](get_kg.cypher).)

---

## Configuration

All settings are read from environment variables in [config.py](config.py).

Required:

- `OPENAI_API_KEY`
- `NEO4J_PASS`

Useful overrides:

- `MODEL_NAME` (default: `gpt-5-nano`)
- `EMBEDDING_MODEL` (default: `text-embedding-3-large`)
- `EMBEDDING_DIMENSIONS` (default: `3072`)
- `NEO4J_URI` (default: `neo4j://localhost:7687`)
- `NEO4J_USER` (default: `neo4j`)
- `NEO4J_DB` (default: `graph.rag.demo`)
- `VECTOR_INDEX` (default: `docs`)
- `RAG_VECTOR_STORE_NAME` (default: `classic-rag-store`)
- `CHUNK_SIZE` / `CHUNK_OVERLAP`

---

## Troubleshooting

- **`OPENAI_API_KEY is not set`**
  - Add it to `.env` or your shell environment.

- **Neo4j auth failures**
  - Ensure `NEO4J_PASS` matches the password configured in [docker-compose.yml](docker-compose.yml).

- **Vector index dimension mismatch**
  - If you change `EMBEDDING_MODEL`, update `EMBEDDING_DIMENSIONS` accordingly, then re-run `zsh rebuild-graph-rag.sh`.

- **Docker volumes / permissions**
  - The compose file mounts into `$HOME/neo4j/*`. If Neo4j fails to start, check permissions and logs:
    - `docker compose logs -f`

---

## Adding your own documents

Drop additional `.md` files into [data/](data/) and re-run:

```bash
zsh rebuild.sh
```
