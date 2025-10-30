import asyncio
import os
import sys

from langchain_text_splitters import RecursiveCharacterTextSplitter
import neo4j
from pathlib import Path

from neo4j_graphrag.experimental.pipeline.kg_builder import SimpleKGPipeline
from neo4j_graphrag.llm import OpenAILLM
from neo4j_graphrag.embeddings import OpenAIEmbeddings
from neo4j_graphrag.experimental.components.text_splitters.langchain import LangChainTextSplitterAdapter
from neo4j_graphrag.llm import OpenAILLM

if __name__ == "__main__":
    # Ensure project root on sys.path when running as a script
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from config import settings, ensure_openai_key
from chunk_utils import get_documents
from config import data
from logger_factory import get_logger
from schema import NODE_TYPES, RELATIONSHIP_TYPES, PATTERNS

log = get_logger("graph_rag.builder")
driver = neo4j.GraphDatabase.driver(settings.uri, auth=(settings.user, settings.password))

async def run_kg_pipeline_with_auto_schema(text: str) -> None:
    """Run the SimpleKGPipeline with automatic schema extraction from text input."""

    # Define LLM parameters
    llm_model_params = {
        # "max_tokens": 2000,
        "response_format": {"type": "json_object"},
        "temperature": 1,  # Lower temperature for more consistent output
    }

    # Create the LLM instance
    llm = OpenAILLM(
        model_name=settings.chat_model,
        model_params=llm_model_params,
    )

    # Create the embedder instance
    embedder = OpenAIEmbeddings()

    try:
        # Create a SimpleKGPipeline instance without providing a schema
        # This will trigger automatic schema extraction
        kg_builder = SimpleKGPipeline(
            llm=llm,
            driver=driver,
            embedder=embedder,
            from_pdf=False, 
            # text_splitter=FixedSizeSplitter(chunk_size=settings.chunk_size, chunk_overlap=settings.chunk_overlap, approximate=False),
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

        # Prepare chunks and run the pipeline chunk-by-chunk
        # documents = chunk_documents(data.text)
        # log.info("Prepared %d chunks", len(documents))

        # for idx, d in enumerate(documents, start=1):
        #     page_content = d.page_content.encode("utf-8")
        #     log.info("Processing chunk %d/%d (%d chars)", idx, len(documents), len(page_content))
        #     await kg_builder.run_async(text=page_content)

        await kg_builder.run_async(text=text)
    except Exception as e:
        log.exception("Error occurred while processing chunks: %s", e)
    finally:
        await llm.async_client.close()


async def main() -> None:
    try:
        ensure_openai_key()

        documents = get_documents()
        
        content = "\n\n".join(d.page_content for d in documents)
        await run_kg_pipeline_with_auto_schema(content)

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