import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass(frozen=True)
class Settings:
    # OpenAI
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")

    # OpenAI Vector Store naming
    vector_store_name: str = os.getenv("RAG_VECTOR_STORE_NAME", "classic-rag-store")

    # Models
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "text-embedding-3-large")
    # Keep this aligned with the embedding model output dimension.
    # text-embedding-3-large -> 3072, text-embedding-3-small -> 1536
    embedding_dimensions: int = int(os.getenv("EMBEDDING_DIMENSIONS", "3072"))
    chat_model: str = os.getenv("MODEL_NAME", "gpt-5-nano")

    # Chunking
    chunk_size: int = int(os.getenv("CHUNK_SIZE", "600"))
    chunk_overlap: int = int(os.getenv("CHUNK_OVERLAP", "120"))

    # Neo4j
    uri: str = os.getenv("NEO4J_URI", "neo4j://localhost:7687")
    user: str = os.getenv("NEO4J_USER", "neo4j")
    password: str = os.getenv("NEO4J_PASS")
    database: str = os.getenv("NEO4J_DB", "graph.rag.demo")

    vector_index: str = os.getenv("VECTOR_INDEX", "docs")

settings = Settings()


def ensure_openai_key():
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is not set. Add it to .env or your shell env.")