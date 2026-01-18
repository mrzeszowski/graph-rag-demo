from pathlib import Path
from typing import List

# LangChain text splitters live in a dedicated distribution.
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

from config import settings
from logger_factory import get_logger

log = get_logger("chunk_utils")

def chunk_documents(raw_text: str, path: Path, doc_index: int) -> List[Document]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        separators=["\n\n", "\n", ". ", " "]
    )
    chunks = splitter.split_text(raw_text)
    # IMPORTANT: "doc_index" identifies the file in this run; "chunk_index" is the position within that file.
    return [
        Document(
            page_content=chunk,
            metadata={"source": path.name, "doc_index": doc_index, "chunk_index": chunk_index},
        )
        for chunk_index, chunk in enumerate(chunks)
    ]

def get_documents() -> List[Document]:

    repo_root = Path(__file__).resolve().parent
    data_dir = repo_root / "data"

    if not data_dir.exists():
        log.error("Data directory not found: %s", data_dir)
        return []

    # Collect all Markdown files
    documents = []
    paths = sorted(data_dir.rglob("*.md"))
    if not paths:
        log.warning("No Markdown files found in %s", data_dir)
        return []

    for i, p in enumerate(paths):
        log.info("Read file %d: %s", i, p)
        text = p.read_text(encoding="utf-8")
        chunks = chunk_documents(text, p, i)
        documents.extend(chunks)

    return documents