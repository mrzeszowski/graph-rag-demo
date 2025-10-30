import argparse
import asyncio
import os
import sys
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
from logger_factory import get_logger

log = get_logger("graph_rag.builder")
driver = GraphDatabase.driver(settings.uri, auth=(settings.user, settings.password))
embedder = OpenAIEmbeddings(model=settings.embedding_model)
retriever = VectorRetriever(driver, settings.vector_index, embedder)

llm = OpenAILLM(model_name=settings.chat_model, model_params={"temperature": 1})

# retriever = Text2CypherRetriever(driver=driver, llm=llm, neo4j_database=settings.database)
# retriever = VectorCypherRetriever(driver, settings.vector_index, "MATCH (n) OPTIONAL MATCH (n)-[r]->(m) RETURN n, r, m;", embedder, )

rag = GraphRAG(retriever=retriever, llm=llm)



def query(question):
    response = rag.search(query_text=question, retriever_config={"top_k": 50})
    # response = rag.search(query_text=question)

    log.info("Question: %s", question)

    log.info("""Answer:\n
------------------------------------------------------
%s
------------------------------------------------------   
""", response.answer)

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