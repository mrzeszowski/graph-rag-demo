import asyncio
import os
import sys
import time

from langchain_text_splitters import RecursiveCharacterTextSplitter
import neo4j

from neo4j_graphrag.experimental.pipeline.kg_builder import SimpleKGPipeline
from neo4j_graphrag.llm import OpenAILLM
from neo4j_graphrag.embeddings import OpenAIEmbeddings
from neo4j_graphrag.experimental.components.text_splitters.langchain import LangChainTextSplitterAdapter

if __name__ == "__main__":
    # Ensure project root on sys.path when running as a script
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from config import settings, ensure_openai_key
from chunk_utils import get_documents
from logger_factory import bind, get_logger, new_run_id
from schema import NODE_TYPES, RELATIONSHIP_TYPES, PATTERNS
from ui import status

log = get_logger("graph_rag.builder")
driver = neo4j.GraphDatabase.driver(settings.uri, auth=(settings.user, settings.password))

def _format_chunk_for_ingest(*, source: str | None, chunk_index: int | None, text: str) -> str:
    # Encode provenance into the text so downstream Chunk nodes can be attributed
    # even if the KG builder does not accept per-chunk metadata.
    header_lines: list[str] = []
    if source:
        header_lines.append(f"SOURCE: {source}")
    if chunk_index is not None:
        header_lines.append(f"CHUNK_INDEX: {chunk_index}")
    if not header_lines:
        return text
    return "\n".join(header_lines) + "\n\n" + text


async def run_kg_pipeline_over_documents(documents) -> None:
    """Run the SimpleKGPipeline over already-chunked Documents, preserving provenance."""

    # Define LLM parameters
    llm_model_params = {
        # "max_tokens": 2000,
        "response_format": {"type": "json_object"},
        # "temperature": 0, not supported in gpt-5-nano
        "top_p": 1.0,
    }

    # Create the LLM instance
    llm = OpenAILLM(
        model_name=settings.chat_model,
        model_params=llm_model_params,
    )

    # Create the embedder instance
    embedder = OpenAIEmbeddings(model=settings.embedding_model)

    try:
        # Reuse one pipeline instance; we already chunk in chunk_utils.
        kg_builder = SimpleKGPipeline(
            llm=llm,
            driver=driver,
            embedder=embedder,
            from_pdf=False, 
            text_splitter=LangChainTextSplitterAdapter(RecursiveCharacterTextSplitter(
                chunk_size=settings.chunk_size,
                chunk_overlap=settings.chunk_overlap,
                separators=["\n\n", "\n", ". ", " "]
            )),
            schema={
                "node_types": NODE_TYPES,
                "relationship_types": RELATIONSHIP_TYPES,
                "patterns": PATTERNS,
            },
            neo4j_database=settings.database  # Using raw text input, not PDF
        )

        total = len(documents) if documents is not None else 0
        for i, d in enumerate(documents or [], start=1):
            src = None
            idx = None
            try:
                src = (d.metadata or {}).get("source")
                idx = (d.metadata or {}).get("chunk_index")
            except Exception:
                src = None
                idx = None

            chunk_text = _format_chunk_for_ingest(source=src, chunk_index=idx, text=d.page_content)
            if i == 1 or i % 25 == 0:
                log.info("Ingesting chunk %d/%d", i, total)
            await kg_builder.run_async(text=chunk_text)
    except Exception as e:
        log.exception("Error occurred while processing chunks: %s", e)
    finally:
        try:
            embedder.client.close()
        except Exception:
            pass
        await llm.async_client.close()


def _backfill_chunk_provenance() -> int:
    """Best-effort: parse SOURCE/CHUNK_INDEX headers into Chunk properties for citations."""
    cypher = """
    MATCH (c:Chunk)
    WHERE c.source IS NULL AND c.text STARTS WITH 'SOURCE:'
    WITH c, split(c.text, '\n') AS lines
    WITH c,
         lines[0] AS l0,
         CASE WHEN size(lines) > 1 THEN lines[1] ELSE '' END AS l1
    SET c.source = trim(replace(l0, 'SOURCE:', ''))
    SET c.source_chunk_index = CASE
        WHEN l1 STARTS WITH 'CHUNK_INDEX:' THEN toInteger(trim(replace(l1, 'CHUNK_INDEX:', '')))
        ELSE c.source_chunk_index
    END
    SET c.index = coalesce(c.index, c.source_chunk_index)
    RETURN count(c) AS updated
    """

    with driver.session(database=settings.database) as session:
        rec = session.run(cypher).single()
        return int(rec["updated"]) if rec and "updated" in rec else 0


def _link_chunks_to_documents_and_next() -> dict:
    """Create :Document nodes and connect :Chunk nodes via :IN_DOC and :NEXT.

    This improves navigability and lets GraphRAG pull structured context even when
    entities are duplicated across chunks.
    """

    create_constraint = """
    CREATE CONSTRAINT document_source_unique IF NOT EXISTS
    FOR (d:Document)
    REQUIRE d.source IS UNIQUE
    """

    link_in_doc = """
    MATCH (c:Chunk)
    WHERE c.source IS NOT NULL
    MERGE (d:Document {source: c.source})
    MERGE (c)-[:IN_DOC]->(d)
    RETURN count(*) AS linked
    """

    link_next = """
    MATCH (d:Document)<-[:IN_DOC]-(c:Chunk)
    WITH d, c
    ORDER BY coalesce(c.source_chunk_index, c.index, 0) ASC
    WITH d, collect(c) AS chunks
    WITH chunks, size(chunks) AS n
    WHERE n >= 2
    UNWIND range(0, n - 2) AS i
    WITH chunks[i] AS c1, chunks[i + 1] AS c2
    MERGE (c1)-[:NEXT]->(c2)
    RETURN count(*) AS created
    """

    with driver.session(database=settings.database) as session:
        session.run(create_constraint)
        linked = session.run(link_in_doc).single()
        created = session.run(link_next).single()

    return {
        "in_doc": int(linked["linked"]) if linked and "linked" in linked else 0,
        "next": int(created["created"]) if created and "created" in created else 0,
    }


async def main() -> None:
    try:
        ensure_openai_key()

        run_id = new_run_id()
        log_ctx = bind(
            log,
            run_id=run_id,
            source="graph_rag",
            op="build",
            model=settings.chat_model,
            embedding_model=settings.embedding_model,
            neo4j_uri=settings.uri,
            neo4j_db=settings.database,
        )

        with status("Reading and chunking documents…"):
            documents = get_documents()
        log_ctx.info("Starting KG pipeline", files=len({d.metadata.get("source") for d in documents}), chunks=len(documents))

        t0 = time.perf_counter()
        with status("Building knowledge graph (GraphRAG)…"):
            await run_kg_pipeline_over_documents(documents)
        log_ctx.info("KG pipeline finished", latency_s=f"{time.perf_counter() - t0:0.2f}")

        with status("Backfilling Chunk provenance…"):
            updated = _backfill_chunk_provenance()
        log_ctx.info("Chunk provenance backfilled", updated=updated)

        with status("Linking chunks to documents…"):
            links = _link_chunks_to_documents_and_next()
        log_ctx.info("Chunk document linking complete", **links)

        # for d in documents:
        #     log.info("Processing document chunk: %s", d.metadata.get("source"))

        #     text = d.page_content
        #     # await define_and_run_pipeline(driver, OpenAILLM(model_name=settings.chat_model), text)
        #     await run_kg_pipeline_with_auto_schema(text)

        # If needed next, pass `documents` to the KG pipeline.
        # 
        # await run_kg_pipeline_with_auto_schema()
    except Exception as e:
        log.exception("Error occurred during knowledge graph pipeline execution: %s", e)
    finally:
        driver.close()


if __name__ == "__main__":
    asyncio.run(main())