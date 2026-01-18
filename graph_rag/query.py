import argparse
import asyncio
import os
import sys
import time

from neo4j import GraphDatabase
from neo4j_graphrag.embeddings import OpenAIEmbeddings
from neo4j_graphrag.generation import GraphRAG
from neo4j_graphrag.llm import OpenAILLM
from neo4j_graphrag.retrievers import VectorCypherRetriever

if __name__ == "__main__":
    # Ensure project root on sys.path when running as a script
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from config import settings, ensure_openai_key
from logger_factory import bind, get_logger, new_run_id
from run_result_writer import write_run_result
from ui import status

log = get_logger("graph_rag.query")
driver = GraphDatabase.driver(settings.uri, auth=(settings.user, settings.password))
embeddings = OpenAIEmbeddings(model=settings.embedding_model)


def _record_to_context(record):
    node = record.get("node") or {}
    score = record.get("score")
    graph_facts = record.get("graph_facts") or []

    text = node.get("text") if isinstance(node, dict) else None
    source = node.get("source") if isinstance(node, dict) else None
    chunk_index = node.get("index") if isinstance(node, dict) else None

    header = []
    if source:
        header.append(f"source={source}")
    if chunk_index is not None:
        header.append(f"chunk_index={chunk_index}")
    if score is not None:
        try:
            header.append(f"score={float(score):0.3f}")
        except Exception:
            header.append(f"score={score}")

    parts = []
    if header:
        parts.append("[" + " | ".join(header) + "]")
    if text:
        parts.append(str(text))

    # Provide a compact neighborhood expansion for graph-augmented retrieval.
    if graph_facts:
        facts_text = "\n".join(f"- {f}" for f in graph_facts if f)
        if facts_text.strip():
            parts.append("Graph context:\n" + facts_text)

    content = "\n\n".join(parts).strip() or str(record)
    metadata = {
        "score": score,
        "source": source,
        "chunk_index": chunk_index,
        "id": record.get("id") or record.get("elementId"),
    }
    return {"content": content, "metadata": metadata}


# Graph-augmented retrieval: vector search gets the best :Chunk nodes, then we
# expand around each chunk in the graph to pull connected entities/relations.
RETRIEVAL_QUERY = """
WITH node, score
OPTIONAL MATCH (node)-[r]-(e)
WITH node, score,
     collect(DISTINCT type(r) + ' -> ' + head(labels(e)) + ':' +
       coalesce(e.name, e.title, e.path, e.adr_num, e.file, e.url, ''))[..40] AS graph_facts
RETURN node { .text, .source, .index } AS node,
       labels(node) AS nodeLabels,
       elementId(node) AS elementId,
       elementId(node) AS id,
       score,
       graph_facts AS graph_facts
"""


def _result_formatter(record):
    # neo4j-graphrag expects RetrieverResultItem(content=..., metadata=...)
    from neo4j_graphrag.types import RetrieverResultItem

    formatted = _record_to_context(record)
    return RetrieverResultItem(content=formatted["content"], metadata=formatted["metadata"])


retriever = VectorCypherRetriever(
    driver,
    settings.vector_index,
    RETRIEVAL_QUERY,
    embeddings,
    result_formatter=_result_formatter,
    neo4j_database=settings.database,
)

llm = OpenAILLM(model_name=settings.chat_model, model_params={"top_p": 1.0})
rag = GraphRAG(retriever=retriever, llm=llm)

def query(question: str) -> str:
    run_id = new_run_id()
    log_ctx = bind(
        log,
        run_id=run_id,
        source="graph_rag",
        op="query",
        model=settings.chat_model,
        embedding_model=settings.embedding_model,
        neo4j_uri=settings.uri,
        neo4j_db=settings.database,
        vector_index=settings.vector_index,
    )

    log_ctx.info("Starting query", question=question)
    t0 = time.perf_counter()
    with status("Running GraphRAG search…"):
        response = rag.search(query_text=question, retriever_config={"top_k": 25})
    log_ctx.info("Search completed", latency_s=f"{time.perf_counter() - t0:0.2f}")
    # response = rag.search(query_text=question)

    log_ctx.info("Question", question=question)

    log_ctx.info("""Answer:\n%s""", response.answer)

    result = write_run_result(question=question, answer=response.answer, source="graph_rag")
    log_ctx.info("Saved run result", path=result.path)
    return response.answer

async def main() -> None:
    try:
        parser = argparse.ArgumentParser(description="Query the using the knowledge graph")
        parser.add_argument("--question", required=True, help="User question")
        args = parser.parse_args()

        ensure_openai_key()
        query(args.question)
    finally:
        driver.close()
        embeddings.client.close()
        llm.client.close()


if __name__ == "__main__":
    asyncio.run(main())