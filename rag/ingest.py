"""Ingest sample text into an OpenAI Vector Store.

Uses LangChain for chunking; uses OpenAI SDK to create the hosted vector store
and upload chunk files. Saves the created vector_store_id to `rag/.rag_store.json`.
"""
from typing import List
import json
import os
import sys
import tempfile

from openai import OpenAI
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

if __name__ == "__main__":
    # Ensure project root on sys.path when running as a script
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from config import settings, ensure_openai_key
from chunk_utils import get_documents
from logger_factory import get_logger

log = get_logger("rag.ingest")

STATE_PATH = os.path.join(os.path.dirname(__file__), ".rag_store.json")

def save_state(vector_store_id: str, file_ids: List[str]) -> None:
    data = {
        "vector_store_id": vector_store_id,
        "file_ids": file_ids,
        "name": settings.vector_store_name,
    }
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def main() -> None:
    ensure_openai_key()
    docs =  get_documents()

    client = OpenAI()
    vs = client.vector_stores.create(name=settings.vector_store_name)

    file_ids: List[str] = []

    # Upload each chunk as a separate file and attach to the vector store
    for i, d in enumerate(docs, start=1):
        log.info("Processing document chunk: %s", d.metadata.get("source"))
        with tempfile.NamedTemporaryFile("w+b", suffix=f"_{i}.txt", delete=False) as tmp:
            tmp.write(d.page_content.encode("utf-8"))
            tmp.flush()
            # Upload file
            with open(tmp.name, "rb") as fh:
                f = client.files.create(file=fh, purpose="assistants")
            file_ids.append(f.id)
            # Attach to store
            client.vector_stores.files.create(vector_store_id=vs.id, file_id=f.id)
        # Best-effort cleanup of temp file
        try:
            os.remove(tmp.name)
        except OSError:
            pass

    save_state(vs.id, file_ids)

    log.info("Created/updated vector store: %s | %s", vs.id, settings.vector_store_name)
    log.info("Attached files: %s", file_ids)

if __name__ == "__main__":
    main()
