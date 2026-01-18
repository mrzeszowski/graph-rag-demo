import argparse
import asyncio
import os
import sys
import time
from dotenv import load_dotenv

from neo4j import GraphDatabase
from neo4j_graphrag.embeddings import OpenAIEmbeddings
from neo4j_graphrag.generation import GraphRAG
from neo4j_graphrag.llm import OpenAILLM
from neo4j_graphrag.retrievers import VectorRetriever, VectorCypherRetriever, Text2CypherRetriever

if __name__ == "__main__":
    # Ensure project root on sys.path when running as a script
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from config import settings, ensure_openai_key
from logger_factory import bind, get_logger, new_run_id
from run_result_writer import write_run_result
from ui import status

log = get_logger("graph_rag.builder")
driver = GraphDatabase.driver(settings.uri, auth=(settings.user, settings.password))
embedder = OpenAIEmbeddings(model=settings.embedding_model)
retriever = VectorRetriever(driver, settings.vector_index, embedder)

llm = OpenAILLM(model_name=settings.chat_model, model_params={"top_p": 1.0})

# retriever = Text2CypherRetriever(driver=driver, llm=llm, neo4j_database=settings.database)
# retriever = VectorCypherRetriever(driver, settings.vector_index, "MATCH (n) OPTIONAL MATCH (n)-[r]->(m) RETURN n, r, m;", embedder, )

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
        response = rag.search(query_text=question, retriever_config={"top_k": 50})
    log_ctx.info("Search completed", latency_s=f"{time.perf_counter() - t0:0.2f}")
    # response = rag.search(query_text=question)

    log_ctx.info("Question", question=question)

    log_ctx.info("""Answer:\n
------------------------------------------------------
%s
------------------------------------------------------   
""", response.answer)

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
        embedder.client.close()
        llm.client.close()


if __name__ == "__main__":
    asyncio.run(main())