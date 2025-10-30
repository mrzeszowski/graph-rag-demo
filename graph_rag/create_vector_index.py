import asyncio
import os
import sys
from timeit import main

from neo4j import GraphDatabase
from neo4j_graphrag.indexes import create_vector_index

if __name__ == "__main__":
    # Ensure project root on sys.path when running as a script
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from config import settings
from logger_factory import get_logger

log = get_logger("graph_rag.create_vector_index")

async def main() -> None:
    driver = GraphDatabase.driver(settings.uri, auth=(settings.user, settings.password))
    try:
        create_vector_index(
            driver,
            settings.vector_index,
            label="Chunk",
            embedding_property="embedding",
            dimensions=3072,
            similarity_fn="cosine", #"euclidean",
        )
    except Exception as e:
        log.exception("Error occurred during vector index creation: %s", e)
    finally:
        driver.close()

if __name__ == "__main__":
    asyncio.run(main())