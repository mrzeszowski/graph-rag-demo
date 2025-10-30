import asyncio
import os
import sys

from neo4j import GraphDatabase
from neo4j_graphrag.embeddings import OpenAIEmbeddings
from neo4j_graphrag.indexes import upsert_vectors
from neo4j_graphrag.types import EntityType

if __name__ == "__main__":
    # Ensure project root on sys.path when running as a script
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from config import settings
from logger_factory import get_logger

log = get_logger("graph_rag.populate_vector_index")

async def main() -> None:
    driver = GraphDatabase.driver(settings.uri, auth=(settings.user, settings.password))
    embedder = OpenAIEmbeddings(model=settings.embedding_model)
    try:
    
        # Fetch real node IDs and texts from Neo4j (update the query as needed)
        ids = []
        texts = []
        with driver.session() as session:
            # TODO: Update the query to match your schema
            results = session.run("MATCH (n:Chunk) RETURN elementId(n) as id, n.text as text, n.embedding as embedding;")
            for record in results:
                ids.append(str(record["id"]))
                texts.append(record["text"])

        # Embed all texts
        embeddings = [embedder.embed_query(t) for t in texts]

        # Upsert vectors with real IDs
        upsert_vectors(
            driver,
            ids=ids,
            embedding_property="embedding",
            embeddings=embeddings,
            entity_type=EntityType.NODE,
        )
    except Exception as e:
        log.exception("Error occurred during vector index creation: %s", e)
    finally:
        driver.close()
        embedder.client.close()

if __name__ == "__main__":
    asyncio.run(main())