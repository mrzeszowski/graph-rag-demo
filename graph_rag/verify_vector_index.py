import argparse
import asyncio
import os
import sys
from typing import Any, Optional

from neo4j import GraphDatabase
from neo4j_graphrag.embeddings import OpenAIEmbeddings
from neo4j_graphrag.retrievers import VectorRetriever

if __name__ == "__main__":
    # Ensure project root on sys.path when running as a script
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from config import ensure_openai_key, settings
from logger_factory import bind, get_logger, new_run_id
from ui import status

log = get_logger("graph_rag.verify_vector_index")


def _get_index_info(session, index_name: str) -> Optional[dict[str, Any]]:
    rec = session.run(
        """
        SHOW INDEXES YIELD name, type, entityType, labelsOrTypes, properties, state, populationPercent, options
        WHERE name = $name
        RETURN name, type, entityType, labelsOrTypes, properties, state, populationPercent, options
        """,
        name=index_name,
    ).single()
    return dict(rec) if rec else None


def _get_embedding_stats(session) -> dict[str, int]:
    rec = session.run(
        """
        MATCH (n:Chunk)
        RETURN
          count(n) AS chunks,
          count(n.embedding) AS with_embedding
        """
    ).single()
    stats = dict(rec) if rec else {"chunks": 0, "with_embedding": 0}

    # Try to compute dimension distribution if embeddings exist
    if stats.get("with_embedding", 0) > 0:
        dim_rec = session.run(
            """
            MATCH (n:Chunk)
            WHERE n.embedding IS NOT NULL
            RETURN size(n.embedding) AS dim, count(*) AS c
            ORDER BY c DESC
            LIMIT 5
            """
        )
        # store as dim_<N>: count
        for r in dim_rec:
            dim = r.get("dim")
            c = r.get("c")
            if isinstance(dim, int) and isinstance(c, int):
                stats[f"dim_{dim}"] = c

    return stats


def _vector_query_nodes(session, index_name: str, query_vector: list[float], top_k: int) -> list[dict[str, Any]]:
    # Neo4j vector index query gives explicit `score` and `node`.
    # This is the most reliable way to confirm the index is functioning.
    rows = session.run(
        """
        CALL db.index.vector.queryNodes($index_name, $k, $vector)
        YIELD node, score
        RETURN elementId(node) AS id,
               score AS score,
               node.text AS text,
               node.index AS chunk_index
        ORDER BY score DESC
        """,
        index_name=index_name,
        k=top_k,
        vector=query_vector,
    )
    return [dict(r) for r in rows]


def _get_any_embedding(session) -> Optional[dict[str, Any]]:
    rec = session.run(
        """
        MATCH (n:Chunk)
        WHERE n.embedding IS NOT NULL
        RETURN elementId(n) AS id, n.embedding AS embedding, n.text AS text
        LIMIT 1
        """
    ).single()
    return dict(rec) if rec else None


async def main() -> None:
    parser = argparse.ArgumentParser(description="Verify Neo4j vector index health for Graph RAG")
    parser.add_argument(
        "--question",
        default="What is this document about?",
        help="A sample question used to test vector retrieval",
    )
    parser.add_argument("--top-k", type=int, default=5, help="How many neighbors to retrieve")
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Do not call OpenAI; use an existing stored embedding as the query vector",
    )
    args = parser.parse_args()

    driver = GraphDatabase.driver(settings.uri, auth=(settings.user, settings.password))
    embedder = None
    if not args.offline:
        ensure_openai_key()
        embedder = OpenAIEmbeddings(model=settings.embedding_model)
    retriever = VectorRetriever(driver, settings.vector_index, embedder, neo4j_database=settings.database)

    run_id = new_run_id()
    log_ctx = bind(
        log,
        run_id=run_id,
        source="graph_rag",
        op="verify_vector_index",
        embedding_model=settings.embedding_model,
        embedding_dimensions=settings.embedding_dimensions,
        neo4j_uri=settings.uri,
        neo4j_db=settings.database,
        vector_index=settings.vector_index,
    )

    try:
        with driver.session(database=settings.database) as session:
            with status("Checking vector index metadata…"):
                idx = _get_index_info(session, settings.vector_index)

            if not idx:
                log_ctx.error("Vector index not found in database", index=settings.vector_index)
                print(
                    f"Vector index '{settings.vector_index}' was not found in database '{settings.database}'.\n"
                    f"Run: python graph_rag/create_vector_index.py"
                )
                return

            log_ctx.info(
                "Index found",
                type=str(idx.get("type")),
                state=str(idx.get("state")),
                populationPercent=idx.get("populationPercent"),
                labelsOrTypes=idx.get("labelsOrTypes"),
                properties=idx.get("properties"),
            )

            print("Index status:")
            print(f"- name: {idx.get('name')}")
            print(f"- type: {idx.get('type')}")
            print(f"- state: {idx.get('state')}")
            print(f"- populationPercent: {idx.get('populationPercent')}")

            options = idx.get("options") or {}
            index_config = options.get("indexConfig") or {}
            idx_dims = index_config.get("vector.dimensions")
            idx_sim = index_config.get("vector.similarity_function")

            if idx_dims is not None and int(idx_dims) != int(settings.embedding_dimensions):
                log_ctx.warning(
                    "Index dimensions mismatch",
                    index_dims=idx_dims,
                    settings_dims=settings.embedding_dimensions,
                )
                print(
                    f"WARNING: index dimensions = {idx_dims}, but settings.embedding_dimensions = {settings.embedding_dimensions}.\n"
                    f"This will break retrieval/upserts or degrade results. Recreate the index with matching dimensions."
                )

            with status("Checking Chunk embedding coverage…"):
                stats = _get_embedding_stats(session)
            log_ctx.info("Chunk stats", **stats)

            chunks = int(stats.get("chunks", 0) or 0)
            with_embedding = int(stats.get("with_embedding", 0) or 0)
            pct = (100.0 * with_embedding / chunks) if chunks else 0.0
            print("Chunk embedding coverage:")
            print(f"- chunks: {chunks}")
            print(f"- with_embedding: {with_embedding} ({pct:0.1f}%)")

            # Direct Cypher vector query (shows real score + elementId)
            with status("Running direct Cypher vector query…"):
                qvec: Optional[list[float]] = None
                if embedder is not None:
                    try:
                        qvec = embedder.embed_query(args.question)
                    except Exception as e:
                        log_ctx.warning("OpenAI embedding call failed; falling back to stored embedding", error=str(e))

                if qvec is None:
                    fallback = _get_any_embedding(session)
                    if not fallback or not fallback.get("embedding"):
                        raise RuntimeError(
                            "Cannot build a query vector: OpenAI is unavailable and no stored Chunk.embedding was found."
                        )
                    qvec = list(fallback["embedding"])
                    fb_id = fallback.get("id")
                    print(
                        "NOTE: OpenAI embedding generation failed/unavailable; using an existing Chunk.embedding as the query vector.\n"
                        f"- chunk_id: {fb_id}"
                    )

                rows = _vector_query_nodes(session, settings.vector_index, qvec, args.top_k)

            if not rows:
                print("Direct Cypher vector query returned 0 results.")
            else:
                print("\nDirect Cypher vector query results:")
                for i, r in enumerate(rows, start=1):
                    snippet = (r.get("text") or "").replace("\n", " ").strip()
                    if len(snippet) > 180:
                        snippet = snippet[:177] + "..."
                    print(f"{i}. score={r.get('score'):0.4f} id={r.get('id')} chunk_index={r.get('chunk_index')} text={snippet}")

        with status("Running a sample vector retrieval…"):
            # Prefer query_vector to avoid OpenAI dependency when offline/fallback.
            if embedder is not None:
                try:
                    result = retriever.search(query_text=args.question, top_k=args.top_k)
                except Exception as e:
                    log_ctx.warning("Retriever text search failed; retrying with query_vector", error=str(e))
                    with driver.session(database=settings.database) as session:
                        fb = _get_any_embedding(session)
                        if not fb or not fb.get("embedding"):
                            raise
                        result = retriever.search(query_vector=list(fb["embedding"]), top_k=args.top_k)
            else:
                with driver.session(database=settings.database) as session:
                    fb = _get_any_embedding(session)
                    if not fb or not fb.get("embedding"):
                        raise RuntimeError("Offline mode requires at least one stored Chunk.embedding")
                    result = retriever.search(query_vector=list(fb["embedding"]), top_k=args.top_k)

        items = getattr(result, "items", None)
        if not items:
            print(
                "Vector retrieval returned 0 results. Likely causes:\n"
                "- No :Chunk nodes with embedding property\n"
                "- Index not ONLINE or built in a different database\n"
                "- Wrong index name in VECTOR_INDEX\n"
            )
            return

        print("OK: Vector retrieval returned results:\n")
        for i, item in enumerate(items, start=1):
            content = getattr(item, "content", None)
            metadata = getattr(item, "metadata", None) or {}
            score = metadata.get("score")
            node_id = metadata.get("id") or metadata.get("elementId")

            snippet = str(content or "").replace("\n", " ").strip()
            if len(snippet) > 180:
                snippet = snippet[:177] + "..."
            if score is not None or node_id is not None:
                print(f"{i}. score={score} id={node_id} text={snippet}")
            else:
                print(f"{i}. text={snippet}")

        print("\nIndex config summary:")
        print(f"- name: {settings.vector_index}")
        print(f"- db: {settings.database}")
        print(f"- model: {settings.embedding_model}")
        print(f"- dimensions: {idx_dims} (settings: {settings.embedding_dimensions})")
        print(f"- similarity: {idx_sim}")

    finally:
        driver.close()
        if embedder is not None:
            embedder.client.close()


if __name__ == "__main__":
    asyncio.run(main())
