from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator, Optional

from rich.console import Console
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
