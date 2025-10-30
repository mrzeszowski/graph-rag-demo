from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys

from openai import OpenAI

STATE_PATH = os.path.join(os.path.dirname(__file__), ".rag_store.json")

if __name__ == "__main__":
    # Ensure project root on sys.path when running as a script
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from config import settings, ensure_openai_key
from logger_factory import get_logger   

log = get_logger("rag.query")
client = OpenAI()

def load_state() -> dict:
    if not os.path.exists(STATE_PATH):
        raise RuntimeError("Vector store not found. Run ingestion first: python rag/ingest.py")
    with open(STATE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def query():
    ensure_openai_key()

    parser = argparse.ArgumentParser(description="Query the OpenAI Vector Store")
    parser.add_argument("--question", required=True, help="User question")
    parser.add_argument("--use-citation", required=False, help="Use citation")
    args = parser.parse_args()

    state = load_state()
    vector_store_id = state["vector_store_id"]

    

    # Use the Responses API with retrieval via the vector store
    response = client.responses.create(
        model=settings.chat_model,
        input=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": args.question,
                    },
                ],
            }
        ],
        # File search tool uses the vector store for retrieval
        tools=[{"type": "file_search", "vector_store_ids": [vector_store_id]}],
        tool_choice="auto",
        metadata={"app": "classic-rag"},
        # Attach our vector store id
        # store={"file_search": {"vector_store_ids": [vector_store_id]}},
    )

    # Extract text answer
    out_text = ""

    # Iterate over all output items; some may be tool calls (e.g., file_search_call)
    if getattr(response, "output", None):
        for item in response.output:
            # We're interested in message items that contain content parts
            if getattr(item, "type", None) == "message" and getattr(item, "content", None):
                for p in item.content:
                    if getattr(p, "type", None) == "output_text":
                        out_text += getattr(p, "text", "")

    log.info("Question:\n %s", args.question)

    log.info("""Answer:\n
------------------------------------------------------
%s
------------------------------------------------------   
""", out_text)


async def main() -> None:
    try:
        ensure_openai_key()
        query()
    except Exception as e:
        log.exception("Error occurred during query: %s", e)
    finally:
        client.close()


if __name__ == "__main__":
    asyncio.run(main())