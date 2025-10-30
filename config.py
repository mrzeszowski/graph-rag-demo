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
    chat_model: str = os.getenv("MODEL_NAME", "gpt-5-mini")

    # Chunking
    chunk_size: int = int(os.getenv("CHUNK_SIZE", "600"))
    chunk_overlap: int = int(os.getenv("CHUNK_OVERLAP", "120"))

    # Neo4j
    uri: str = os.getenv("NEO4J_URI", "neo4j://localhost:7687")
    user: str = os.getenv("NEO4J_USER", "neo4j")
    password: str = os.getenv("NEO4J_PASS", "password")
    database: str = os.getenv("NEO4J_DB", "graph.rag.demo")

    vector_index: str = os.getenv("VECTOR_INDEX", "docs")

settings = Settings()


def ensure_openai_key():
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is not set. Add it to .env or your shell env.")


@dataclass(frozen=True)
class Data:
    text: str = """
Anna Kowalska bought a car from AutoWorld, a dealership in Warsaw. 
The car was manufactured by CarTech, where Jan Nowak works as a senior engineer. 
Jan’s colleague, Maria Zielińska, is responsible for quality assurance at CarTech.

After the purchase, Anna insured the car through SafeDrive Insurance. 
The insurance broker was Piotr Wiśniewski, who collaborates with AutoWorld on multiple contracts.

Later, Anna’s car required servicing at QuickFix Garage, a partner of CarTech. 
QuickFix Garage employs several mechanics, including Tomasz Malinowski, who previously worked at AutoWorld.

Meanwhile, CarTech signed a strategic partnership with GreenEnergy Corp to develop electric vehicle batteries. 
Maria Zielińska is leading the joint research team with GreenEnergy’s CTO, Laura Chen.

Anna is a member of the Warsaw Drivers Association, which often organizes events in collaboration with SafeDrive Insurance.
"""
    
data = Data()