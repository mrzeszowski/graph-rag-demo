from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import time
import textwrap
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Optional

from openai import OpenAI

if __name__ == "__main__":
    # Ensure project root on sys.path when running as a script
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import ensure_openai_key, settings
from logger_factory import bind, get_logger, new_run_id
from ui import status


log = get_logger("verify_latest_run")


_RUN_FILE_RE = re.compile(r"^run_(\d{4})\.txt$")

_RECORD_DELIM = "----- RUN RECORD -----"


@dataclass(frozen=True)
class RunRecord:
    path: str
    run_number: int
    timestamp: Optional[datetime]
    source: str
    question: str
    answer: str


def _project_root() -> str:
    return os.path.dirname(os.path.abspath(__file__))


def _default_run_dir() -> str:
    return os.path.join(_project_root(), "run_results")


def _iter_run_files(run_dir: str) -> Iterable[tuple[int, str]]:
    """Yield (run_number, path) for run_XXXX.txt files in run_dir."""
    if not os.path.isdir(run_dir):
        return

    for name in os.listdir(run_dir):
        match = _RUN_FILE_RE.match(name)
        if not match:
            continue
        run_number = int(match.group(1))
        yield run_number, os.path.join(run_dir, name)


def _find_latest_run_file(
    run_dir: str,
    *,
    require_sources: Optional[set[str]] = None,
) -> Optional[str]:
    """Return newest run file path.

    If require_sources is provided, prefer the newest file that contains at
    least one record for each required source.
    """

    files = sorted(_iter_run_files(run_dir), key=lambda p: p[0], reverse=True)
    if not files:
        return None

    if not require_sources:
        return files[0][1]

    for _, path in files:
        sources: set[str] = set()
        for r in parse_run_file_records(path):
            if r.source:
                sources.add(r.source)
        if require_sources.issubset(sources):
            return path

    return files[0][1]


def _parse_timestamp(line: str) -> Optional[datetime]:
    # Expected: timestamp: 2026-01-17T17:30:23.434121+01:00
    if not line.lower().startswith("timestamp:"):
        return None
    value = line.split(":", 1)[1].strip()
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _parse_source(line: str) -> Optional[str]:
    if not line.lower().startswith("source:"):
        return None
    value = line.split(":", 1)[1].strip()
    return value or None


def _split_question_answer(text: str) -> tuple[str, str]:
    # File format is produced by run_result_writer.write_run_result
    # with blocks:
    # Question:\n...\n\nAnswer:\n...
    q_marker = "\nQuestion:\n"
    a_marker = "\n\nAnswer:\n"

    q_idx = text.find(q_marker)
    if q_idx == -1:
        return "", text.strip()

    after_q = text[q_idx + len(q_marker) :]
    a_idx = after_q.find(a_marker)
    if a_idx == -1:
        return after_q.strip(), ""

    question = after_q[:a_idx].strip()
    answer = after_q[a_idx + len(a_marker) :].strip()
    return question, answer


def _parse_single_record(*, path: str, run_number: int, raw: str) -> RunRecord:
    lines = raw.splitlines()
    timestamp: Optional[datetime] = None
    source: str = ""

    for line in lines[:8]:
        timestamp = timestamp or _parse_timestamp(line)
        parsed_source = _parse_source(line)
        if parsed_source:
            source = parsed_source

    question, answer = _split_question_answer(raw)

    return RunRecord(
        path=path,
        run_number=run_number,
        timestamp=timestamp,
        source=source,
        question=question,
        answer=answer,
    )


def parse_run_file(path: str) -> RunRecord:
    basename = os.path.basename(path)
    match = _RUN_FILE_RE.match(basename)
    if not match:
        raise ValueError(f"Not a run file: {path}")

    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()

    # Back-compat: older files contain a single record.
    # Session files contain multiple records separated by a delimiter line.
    if _RECORD_DELIM not in raw:
        return _parse_single_record(path=path, run_number=int(match.group(1)), raw=raw)

    # If multiple records exist, return the last *valid* one for this legacy API.
    records = list(parse_run_file_records(path))
    if not records:
        return _parse_single_record(path=path, run_number=int(match.group(1)), raw=raw)
    return records[-1]


def parse_run_file_records(path: str) -> Iterable[RunRecord]:
    basename = os.path.basename(path)
    match = _RUN_FILE_RE.match(basename)
    if not match:
        return []

    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()

    run_number = int(match.group(1))

    if _RECORD_DELIM not in raw:
        r = _parse_single_record(path=path, run_number=run_number, raw=raw)
        if r.question.strip():
            yield r
        return

    parts = raw.split(_RECORD_DELIM)
    for part in parts:
        part = part.strip()
        if not part:
            continue
        # Re-add minimal structure so the existing split markers work reliably.
        candidate = part
        r = _parse_single_record(path=path, run_number=run_number, raw=candidate)
        if not r.question.strip():
            continue
        yield r


def iter_run_records(run_dir: str) -> Iterable[RunRecord]:
    if not os.path.isdir(run_dir):
        return []

    for name in os.listdir(run_dir):
        match = _RUN_FILE_RE.match(name)
        if not match:
            continue
        path = os.path.join(run_dir, name)
        try:
            yield from parse_run_file_records(path)
        except Exception:
            # Skip malformed entries
            continue


def _record_sort_key(r: RunRecord) -> tuple:
    # Prefer timestamp, then run number.
    ts = r.timestamp.timestamp() if r.timestamp else 0
    return (ts, r.run_number)


def find_latest_pair(
    run_dir: str,
    source_a: str,
    source_b: str,
) -> tuple[Optional[RunRecord], Optional[RunRecord]]:
    records = list(iter_run_records(run_dir))
    if not records:
        return None, None

    # Group by exact question text; for each question keep latest record per source.
    grouped: dict[str, dict[str, RunRecord]] = {}
    for r in records:
        if not r.question:
            continue
        by_source = grouped.setdefault(r.question, {})
        existing = by_source.get(r.source)
        if not existing or _record_sort_key(r) > _record_sort_key(existing):
            by_source[r.source] = r

    best_q: Optional[str] = None
    best_key: Optional[tuple] = None

    for q, per_source in grouped.items():
        if source_a in per_source and source_b in per_source:
            a = per_source[source_a]
            b = per_source[source_b]
            key = max(_record_sort_key(a), _record_sort_key(b))
            if best_key is None or key > best_key:
                best_key = key
                best_q = q

    if best_q is not None:
        per_source = grouped[best_q]
        return per_source[source_a], per_source[source_b]

    # Fallback: latest per source even if questions differ
    latest_a = None
    latest_b = None
    for r in records:
        if r.source == source_a and (latest_a is None or _record_sort_key(r) > _record_sort_key(latest_a)):
            latest_a = r
        if r.source == source_b and (latest_b is None or _record_sort_key(r) > _record_sort_key(latest_b)):
            latest_b = r

    return latest_a, latest_b


def _extract_output_text(response) -> str:
    out_text = ""
    if getattr(response, "output", None):
        for item in response.output:
            if getattr(item, "type", None) == "message" and getattr(item, "content", None):
                for part in item.content:
                    if getattr(part, "type", None) == "output_text":
                        out_text += getattr(part, "text", "")
    return out_text.strip()


def _extract_first_json_object(text: str) -> Optional[dict]:
    """Extract and parse the first JSON object from text.

    Models sometimes wrap JSON in prose or Markdown fences; this attempts to
    robustly recover the object without being overly clever.
    """
    if not text:
        return None

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None

    candidate = text[start : end + 1].strip()
    try:
        data = json.loads(candidate)
    except Exception:
        return None

    return data if isinstance(data, dict) else None


def _terminal_width(default: int = 100) -> int:
    try:
        width = shutil.get_terminal_size(fallback=(default, 24)).columns
        return max(60, min(160, int(width)))
    except Exception:
        return default


def _wrap_paragraph(text: str, *, width: int, indent: str = "") -> str:
    return textwrap.fill(
        text.strip(),
        width=width,
        initial_indent=indent,
        subsequent_indent=indent,
        break_long_words=False,
        break_on_hyphens=False,
    )


def _format_assessment_report(data: dict, *, max_bullets: int = 6) -> Optional[str]:
    """Format evaluator JSON into a terminal-friendly report."""
    assessments = data.get("assessments")
    executive = data.get("executive")
    if not isinstance(assessments, list) or not assessments:
        return None

    try:
        max_bullets = int(max_bullets)
    except Exception:
        max_bullets = 6
    max_bullets = max(1, min(12, max_bullets))

    width = _terminal_width()
    lines: list[str] = []

    lines.append("GraphRAG vs RAG – Assessment Report")
    lines.append("=" * min(width, 34))

    for idx, item in enumerate(assessments, start=1):
        if not isinstance(item, dict):
            continue
        question = str(item.get("question", "")).strip()
        gr = item.get("graph_rag_score")
        rag = item.get("rag_score")
        winner = str(item.get("winner", "")).strip()
        rationale = item.get("rationale")

        if question:
            lines.append("")
            lines.append(_wrap_paragraph(f"[{idx}] Q: {question}", width=width))

        score_line = f"    GraphRAG: {gr}/10 | RAG: {rag}/10"
        if winner:
            score_line += f" | Winner: {winner}"
        lines.append(_wrap_paragraph(score_line, width=width))

        if isinstance(rationale, list) and rationale:
            for bullet in rationale[:max_bullets]:
                b = str(bullet).strip()
                if not b:
                    continue
                lines.append(_wrap_paragraph(f"    - {b}", width=width))

    if isinstance(executive, dict):
        summary = executive.get("summary")
        highlights = executive.get("highlights")
        graph_better = executive.get("graph_rag_clearly_better")
        rag_better = executive.get("rag_clearly_better")
        ties = executive.get("ties_or_inconclusive")

        lines.append("")
        lines.append("Executive report")
        lines.append("=" * min(width, 16))

        if isinstance(summary, str) and summary.strip():
            lines.append(_wrap_paragraph(summary, width=width))

        def _emit_list(title: str, items) -> None:
            if not isinstance(items, list) or not items:
                return
            lines.append("")
            lines.append(title)
            for it in items[:8]:
                s = str(it).strip()
                if s:
                    lines.append(_wrap_paragraph(f"- {s}", width=width))

        _emit_list("GraphRAG clearly outperforms RAG:", graph_better)
        _emit_list("RAG closed the gap / outperformed GraphRAG:", rag_better)
        _emit_list("Ties / insufficient delta:", ties)

        if isinstance(highlights, list) and highlights:
            lines.append("")
            lines.append("Key outcomes:")
            for h in highlights[:8]:
                s = str(h).strip()
                if s:
                    lines.append(_wrap_paragraph(f"- {s}", width=width))

    return "\n".join(lines).strip() + "\n"


def build_comparison_prompt(*, results_text: str, max_bullets: int = 6) -> list[dict]:
    try:
        max_bullets = int(max_bullets)
    except Exception:
        max_bullets = 6
    max_bullets = max(1, min(12, max_bullets))

    system_text = (
        """
You are an expert evaluator specializing in:
- Retrieval-Augmented Generation (RAG)
- GraphRAG / Knowledge-Graph-based reasoning
- Architecture Decision Records (ADRs)
- Architecture governance, auditability, and semantic correctness

You will evaluate and compare **GraphRAG** and **classical RAG** answers
based strictly on the provided execution results.

You must:
- Compare GraphRAG vs RAG answers **per question**
- Score each answer on a **0–10 integer scale**
- Prioritize **architectural usefulness and semantic correctness**, not verbosity
- Be conservative and precise — do not hallucinate missing facts
- Base all judgments only on the supplied results

### Scoring rules (CRITICAL)
These rules override all other heuristics:
1) **Scope control is the #1 criterion.**
   - If an answer materially expands beyond what the question asks ("scope creep"), it must be penalized.
   - **Do NOT reward breadth.** More ADRs or extra narrative is not better unless the question explicitly asks for it.

2) **Factual discipline / non-hallucination.**
   - If an answer introduces concrete entities (ADRs, services, products, tools) that are not supported by the shown results,
     penalize heavily.

3) **Structural fidelity to ADR semantics.**
   - Correct use of relationships like `supersedes`, `amends`, and clear separation of decisions vs alternatives.

4) **Auditability.**
   - Prefer answers that anchor claims to specific ADR ids/dates/relations present in the answers.

### Hard caps (to avoid "nice story" scoring)
Apply these caps strictly:
- If the answer is mostly correct but includes **clear scope creep**: score must be **<= 6**.
- If the answer includes **specific examples not grounded** (e.g., naming services/tools not evidenced): score must be **<= 5**.
- If the answer is both off-scope and adds ungrounded specifics: score must be **<= 3**.

### Example guidance (DO NOT quote this in output)
If asked: "Timeline of messaging platform decisions?"
- Only ADRs about messaging platform decisions (e.g., Kafka/Pub/Sub) and directly relevant lineage metadata are in-scope.
- Adding auth, API gateway, schema governance ADRs is out-of-scope unless the question explicitly asks for a broader org timeline.

### Output requirements (STRICT)
Return a single JSON object only (no Markdown, no prose, no code fences).

### Brevity requirements (STRICT)
Write like a slide deck / exec brief:
- Use short, telegraphic bullets (fragments; no long sentences)
- No filler, no hedging, no repeating the full answers
- Prefer 1 clause per bullet
- Do not quote large chunks of the answers
- Keep outputs compact and scannable

The JSON schema must be:
{
    "assessments": [
        {
            "question": string,
            "graph_rag_score": integer 0-10,
            "rag_score": integer 0-10,
            "winner": "graph_rag" | "rag" | "tie" | "inconclusive",
            "rationale": [string, ...]  // 1-{MAX_BULLETS} concise bullets, architecture-focused
        }
    ],
    "executive": {
        "summary": string, // 1-2 short sentences (<= 30 words total)
        "graph_rag_clearly_better": [string, ...],
        "rag_clearly_better": [string, ...],
        "ties_or_inconclusive": [string, ...],
        "highlights": [string, ...] // up to 5 bullets
    }
}

Rules:
- Scores must be integers 0-10
- Keep each bullet very short (<= 90 chars)
- Keep each list short (<= 5 items), unless explicitly required by the schema
- If information is insufficient to judge a delta, use winner="inconclusive" and explain why
- Base all judgments only on the supplied results

If you cannot comply with brevity, reduce detail rather than adding text.

### Style rules
- Professional, analytical, architect-level tone
- No emojis
- No speculation
- No references to prompt mechanics
- No repetition of raw answers unless necessary for justification
        """
    )

    user_text_template = (
        """
Below are execution results for the same set of questions,
answered using two approaches:
- GraphRAG
- classical RAG

The results include:
- questions
- answers
- source labels (graph_rag / rag)

Your task:
1. Compare GraphRAG and RAG answers **per question**
2. Produce a single JSON object following the required schema

### Important constraints
- Base your evaluation ONLY on the results below
- Do NOT assume additional context
- Do NOT infer intent beyond what is visible in the answers
- Scores must reflect **architectural reasoning quality**, not verbosity

### Placeholder: Evaluation Input
Insert the full run results below.

{RESULTS}

### Optional context (if present)
If a prior baseline/evaluation is not included in the input, state that clearly and do not invent one.
        """
    )

    user_text = user_text_template.replace("{RESULTS}", results_text)

    return [
        {
            "role": "system",
            "content": [
                {
                    "type": "input_text",
                    "text": system_text.replace("{MAX_BULLETS}", str(max_bullets)),
                }
            ],
        },
        {
            "role": "user",
            "content": [{"type": "input_text", "text": user_text}],
        },
    ]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate newest Classic RAG vs GraphRAG run file results and print differences."
    )
    parser.add_argument("--run-dir", default=_default_run_dir(), help="Directory with run_XXXX.txt files")
    parser.add_argument(
        "--run-file",
        default=None,
        help="Explicit run_XXXX.txt file to evaluate (default: newest file containing both sources)",
    )
    parser.add_argument("--source-a", default="rag", help="Source name for classic RAG (default: rag)")
    parser.add_argument("--source-b", default="graph_rag", help="Source name for graph RAG (default: graph_rag)")
    parser.add_argument("--model", default=settings.chat_model, help="OpenAI model for comparison")
    parser.add_argument("--max-bullets", type=int, default=6, help="Max number of difference bullets")
    args = parser.parse_args()

    run_id = new_run_id()
    log_ctx = bind(
        log,
        run_id=run_id,
        op="verify_latest_run",
        model=args.model,
        source_a=args.source_a,
        source_b=args.source_b,
    )

    ensure_openai_key()

    run_path: Optional[str] = None
    if args.run_file:
        run_path = args.run_file
        if not os.path.isabs(run_path):
            run_path = os.path.join(args.run_dir, run_path)
        if not os.path.isfile(run_path):
            log_ctx.error("Run file not found", path=run_path)
            return 2
    else:
        run_path = _find_latest_run_file(
            args.run_dir,
            require_sources={args.source_a, args.source_b},
        )

    if not run_path:
        log_ctx.error("No run results found", run_dir=args.run_dir)
        return 2

    with open(run_path, "r", encoding="utf-8") as f:
        results_text = f.read().strip()

    if not results_text:
        log_ctx.error("Run file is empty", path=run_path)
        return 2

    log_ctx.info("Evaluating run file", path=run_path, bytes=len(results_text.encode("utf-8")))

    prompt = build_comparison_prompt(results_text=results_text)

    client = OpenAI()
    try:
        t0 = time.perf_counter()
        with status("Calling OpenAI to compare GraphRAG vs RAG…"):
            resp = client.responses.create(
                model="gpt-5.2", # args.model,
                input=prompt,
                top_p=1.0,
                metadata={
                    "app": "verify-latest-run",
                    "run_id": run_id,
                    "source_a": args.source_a,
                    "source_b": args.source_b,
                },
            )
        log_ctx.info("Comparison complete", latency_s=f"{time.perf_counter() - t0:0.2f}")
        raw_text = _extract_output_text(resp)
        parsed = _extract_first_json_object(raw_text)
        formatted = _format_assessment_report(parsed, max_bullets=args.max_bullets) if parsed else None
        print(formatted or raw_text)
        return 0
    finally:
        client.close()


if __name__ == "__main__":
    raise SystemExit(main())
