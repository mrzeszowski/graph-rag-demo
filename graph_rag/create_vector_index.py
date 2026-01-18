import asyncio
import os
import sys

from neo4j import GraphDatabase
from neo4j_graphrag.indexes import create_vector_index

if __name__ == "__main__":
    # Ensure project root on sys.path when running as a script
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from config import settings
from logger_factory import bind, get_logger, new_run_id
from ui import status

log = get_logger("graph_rag.create_vector_index")

async def main() -> None:
    driver = GraphDatabase.driver(settings.uri, auth=(settings.user, settings.password))

    run_id = new_run_id()
    log_ctx = bind(
        log,
        run_id=run_id,
        source="graph_rag",
        op="create_vector_index",
        neo4j_uri=settings.uri,
        neo4j_db=settings.database,
        vector_index=settings.vector_index,
    )
    try:
        log_ctx.info("Creating vector index")
        with status("Creating Neo4j vector index…"):
            create_vector_index(
                driver,
                settings.vector_index,
                label="Chunk",
                embedding_property="embedding",
                dimensions=settings.embedding_dimensions,
                similarity_fn="cosine", #"euclidean",
                neo4j_database=settings.database,
            )
        log_ctx.info("Vector index created")
    except Exception as e:
        log.exception("Error occurred during vector index creation: %s", e)
    finally:
        driver.close()

if __name__ == "__main__":
    asyncio.run(main())