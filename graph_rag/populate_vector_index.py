import asyncio
import os
import sys
import time

from neo4j import GraphDatabase
from neo4j_graphrag.embeddings import OpenAIEmbeddings
from neo4j_graphrag.indexes import upsert_vectors
from neo4j_graphrag.types import EntityType

if __name__ == "__main__":
    # Ensure project root on sys.path when running as a script
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from config import settings
from logger_factory import bind, get_logger, new_run_id
from ui import progress_task, status

log = get_logger("graph_rag.populate_vector_index")

async def main() -> None:
    driver = GraphDatabase.driver(settings.uri, auth=(settings.user, settings.password))
    embedder = OpenAIEmbeddings(model=settings.embedding_model)

    run_id = new_run_id()
    log_ctx = bind(
        log,
        run_id=run_id,
        source="graph_rag",
        op="populate_vector_index",
        embedding_model=settings.embedding_model,
        neo4j_uri=settings.uri,
        neo4j_db=settings.database,
        vector_index=settings.vector_index,
    )
    try:

        # Fetch real node IDs and texts from Neo4j (update the query as needed)
        ids = []
        texts = []
        with status("Fetching Chunk nodes from Neo4j…"):
            with driver.session(database=settings.database) as session:
                results = session.run(
                    "MATCH (n:Chunk) RETURN elementId(n) as id, n.text as text, n.embedding as embedding;"
                )
                for record in results:
                    ids.append(str(record["id"]))
                    texts.append(record["text"])

        log_ctx.info("Fetched nodes", count=len(ids))
        if not texts:
            log_ctx.warning("No texts found to embed; skipping upsert")
            return

        # Embed all texts
        embeddings = []
        with progress_task(description="Embedding Chunk texts…", total=len(texts)) as (progress, task_id):
            for i, t in enumerate(texts, start=1):
                t0 = time.perf_counter()
                emb = embedder.embed_query(t)
                embeddings.append(emb)
                progress.update(task_id, advance=1)
                if i == 1 or i % 25 == 0:
                    log_ctx.debug("Embedded", at=i, latency_s=f"{time.perf_counter() - t0:0.2f}")

        # Upsert vectors with real IDs
        with status("Upserting vectors into Neo4j index…"):
            upsert_vectors(
                driver,
                ids=ids,
                embedding_property="embedding",
                embeddings=embeddings,
                entity_type=EntityType.NODE,
            )
        log_ctx.info("Vector upsert completed", count=len(ids))
    except Exception as e:
        log.exception("Error occurred during vector index creation: %s", e)
    finally:
        driver.close()
        embedder.client.close()

if __name__ == "__main__":
    asyncio.run(main())