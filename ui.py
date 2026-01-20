from __future__ import annotations

from contextlib import contextmanager
import os
import sys
from typing import Iterator, Optional

from rich.console import Console
from rich import box
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskID,
    TextColumn,
    TimeElapsedColumn,
)


_console: Optional[Console] = None


def get_console() -> Console:
    global _console
    if _console is None:
        _console = Console()
    return _console


@contextmanager
def status(message: str) -> Iterator[None]:
    """Show a spinner/status while doing a blocking operation."""
    console = get_console()
    with console.status(message):
        yield


def make_progress(*, transient: bool = True) -> Progress:
    """A standard progress bar used across scripts."""
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total}"),
        TimeElapsedColumn(),
        transient=transient,
        console=get_console(),
    )


@contextmanager
def progress_task(*, description: str, total: int, transient: bool = True) -> Iterator[tuple[Progress, TaskID]]:
    progress = make_progress(transient=transient)
    with progress:
        task_id = progress.add_task(description, total=total)
        yield progress, task_id


def print_qa_block(*, question: str, answer: str, title: str = "RESULT") -> None:
    """Print a clearly separated Question/Answer block (not via logging).

    This helps the Q/A stand out from noisy logs.
    """

    console = get_console()
    q = (question or "").strip()
    a = (answer or "").strip() or "(empty)"

    console.print()
    console.rule(f"[bold]{title}[/bold]")
    console.print(
        Panel(
            q,
            title="Question",
            border_style="cyan",
            box=box.ROUNDED,
            expand=True,
        )
    )
    console.print(
        Panel(
            a,
            title="Answer",
            border_style="green",
            box=box.ROUNDED,
            expand=True,
        )
    )
    console.rule()
    console.print()


def wait_for_enter(*, prompt: str = "Press Enter to continue…", env_var: str = "NO_PAUSE") -> None:
    """Wait for Enter in interactive terminals.

    Skips waiting when stdin is not a TTY (e.g., CI/pipes) or when env_var is truthy.
    """

    if os.getenv(env_var, "").strip().lower() in {"1", "true", "yes", "on"}:
        return
    if not getattr(sys.stdin, "isatty", lambda: False)():
        return
    try:
        input(prompt)
    except (EOFError, KeyboardInterrupt):
        return
