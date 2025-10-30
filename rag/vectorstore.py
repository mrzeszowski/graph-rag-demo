from typing import Optional

from langchain_openai import OpenAIVectorStore, OpenAIEmbeddings

from config import settings


def get_vectorstore(embeddings: Optional[OpenAIEmbeddings] = None) -> OpenAIVectorStore:
    """Return a handle to the OpenAI Vector Store using configured names.

    Assumes the store/collection was created during ingestion.
    """
    if embeddings is None:
        embeddings = OpenAIEmbeddings(model=settings.embedding_model)

    # Construct a handle to the named store + collection.
    # The LangChain partner integration connects to OpenAI's hosted Vector Stores.
    vs = OpenAIVectorStore(
        embedding=embeddings,
        collection_name=settings.vector_store_index,
        vectorstore_name=settings.vector_store_name,
    )
    return vs
