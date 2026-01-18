from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional


_RUN_FILE_RE = re.compile(r"^run_(\d{4})\.txt$")

# If set, all results will be appended into this single file.
# Intended usage: `run.sh` creates a new session file once and exports this env var
# so the subsequent per-question runs append into the same run_XXXX.txt.
_SESSION_PATH_ENV = "RUN_RESULTS_PATH"

# Delimiter between records when appending into a session file.
_RECORD_DELIM = "\n\n----- RUN RECORD -----\n"


@dataclass(frozen=True)
class RunResult:
    path: str
    run_number: int


def _project_root() -> str:
    return os.path.dirname(os.path.abspath(__file__))


def _run_result_dir() -> str:
    return os.path.join(_project_root(), "run_results")


def _next_run_number(directory: str) -> int:
    try:
        entries = os.listdir(directory)
    except FileNotFoundError:
        return 1

    max_n = 0
    for name in entries:
        match = _RUN_FILE_RE.match(name)
        if not match:
            continue
        max_n = max(max_n, int(match.group(1)))

    return max_n + 1


def _parse_run_number_from_path(path: str) -> int:
    basename = os.path.basename(path)
    match = _RUN_FILE_RE.match(basename)
    if not match:
        return 0
    return int(match.group(1))


def create_run_session_file(*, header: Optional[str] = None) -> RunResult:
    """Create a new run_XXXX.txt file and return its path.

    This is meant to be called once per `run.sh` execution. Individual query runs
    should then append their Question/Answer records into this file via
    `RUN_RESULTS_PATH`.
    """

    directory = _run_result_dir()
    os.makedirs(directory, exist_ok=True)

    run_number = _next_run_number(directory)
    filename = f"run_{run_number:04d}.txt"
    path = os.path.join(directory, filename)

    now = datetime.now(timezone.utc).astimezone()

    with open(path, "w", encoding="utf-8") as f:
        f.write(f"timestamp: {now.isoformat()}\n")
        f.write("session: true\n")
        if header:
            f.write(f"header: {header.strip()}\n")
        f.write("\n")

    return RunResult(path=path, run_number=run_number)


def write_run_result(*, question: str, answer: str, source: Optional[str] = None) -> RunResult:
    """Write a query run result.

    Default behavior: creates a new `run_results/run_XXXX.txt` file per call.

    Session behavior: if the env var `RUN_RESULTS_PATH` is set, appends the
    result as a new record into that file. This enables one output file per
    `run.sh` execution.
    """

    session_path = os.environ.get(_SESSION_PATH_ENV)
    if session_path:
        os.makedirs(os.path.dirname(session_path), exist_ok=True)
        now = datetime.now(timezone.utc).astimezone()
        with open(session_path, "a", encoding="utf-8") as f:
            f.write(_RECORD_DELIM)
            f.write(f"timestamp: {now.isoformat()}\n")
            if source:
                f.write(f"source: {source}\n")
            f.write("\n")
            f.write("Question:\n")
            f.write(question.strip())
            f.write("\n\n")
            f.write("Answer:\n")
            f.write(answer.strip())
            f.write("\n")

        return RunResult(path=session_path, run_number=_parse_run_number_from_path(session_path))

    directory = _run_result_dir()
    os.makedirs(directory, exist_ok=True)

    run_number = _next_run_number(directory)
    filename = f"run_{run_number:04d}.txt"
    path = os.path.join(directory, filename)

    now = datetime.now(timezone.utc).astimezone()

    with open(path, "w", encoding="utf-8") as f:
        f.write(f"timestamp: {now.isoformat()}\n")
        if source:
            f.write(f"source: {source}\n")
        f.write("\n")
        f.write("Question:\n")
        f.write(question.strip())
        f.write("\n\n")
        f.write("Answer:\n")
        f.write(answer.strip())
        f.write("\n")

    return RunResult(path=path, run_number=run_number)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run result writer utilities")
    parser.add_argument(
        "--start-session",
        action="store_true",
        help="Create a new run_XXXX.txt session file and print its path",
    )
    parser.add_argument(
        "--header",
        required=False,
        help="Optional header line to write into the session file",
    )
    args = parser.parse_args()

    if args.start_session:
        result = create_run_session_file(header=args.header)
        print(result.path)
