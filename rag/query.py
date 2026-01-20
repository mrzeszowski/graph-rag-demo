from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time

from openai import OpenAI

STATE_PATH = os.path.join(os.path.dirname(__file__), ".rag_store.json")

if __name__ == "__main__":
    # Ensure project root on sys.path when running as a script
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from config import settings, ensure_openai_key
from logger_factory import bind, get_logger, new_run_id
from run_result_writer import write_run_result
from ui import print_qa_block, status, wait_for_enter

log = get_logger("rag.query")
client = OpenAI()


def build_graphrag_like_messages(*, question: str) -> list[dict]:
    system_text = "Answer the user question using the provided context."
    user_text = f"""Question:
{question}

Answer:
"""
    return [
        {
            "role": "system",
            "content": [{"type": "input_text", "text": system_text}],
        },
        {
            "role": "user",
            "content": [{"type": "input_text", "text": user_text}],
        },
    ]

def load_state() -> dict:
    if not os.path.exists(STATE_PATH):
        raise RuntimeError("Vector store not found. Run ingestion first: python rag/ingest.py")
    with open(STATE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def query():
    ensure_openai_key()

    run_id = new_run_id()
    log_ctx = bind(log, run_id=run_id, source="rag", model=settings.chat_model)

    parser = argparse.ArgumentParser(description="Query the OpenAI Vector Store")
    parser.add_argument("--question", required=True, help="User question")
    parser.add_argument("--use-citation", required=False, help="Use citation")
    args = parser.parse_args()

    state = load_state()
    vector_store_id = state["vector_store_id"]

    log_ctx.info("Starting query")

    t0 = time.perf_counter()
    with status("Calling OpenAI (classic RAG)…"):
        # Use the Responses API with retrieval via the vector store
        response = client.responses.create(
            model=settings.chat_model,
            input=build_graphrag_like_messages(question=args.question),
            # File search tool uses the vector store for retrieval
            tools=[{"type": "file_search", "vector_store_ids": [vector_store_id]}],
            tool_choice="auto",
            metadata={"app": "classic-rag", "run_id": run_id},
            top_p=1.0,
        )
    log_ctx.info("OpenAI response received", latency_s=f"{time.perf_counter() - t0:0.2f}")

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

    print_qa_block(question=args.question, answer=out_text, title="RAG")

    result = write_run_result(question=args.question, answer=out_text, source="rag")
    log_ctx.info("Saved run result", path=result.path)


async def main() -> None:
    try:
        ensure_openai_key()
        query()
        wait_for_enter()
    except Exception as e:
        log.exception("Error occurred during query: %s", e)
    finally:
        client.close()


if __name__ == "__main__":
    asyncio.run(main())