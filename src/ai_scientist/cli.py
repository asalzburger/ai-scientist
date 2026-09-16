from __future__ import annotations

from pathlib import Path

import typer

from .agent import ScientistAgent
from .config import Settings
from .context import ContextBuilder
from .domain import Project, Status, Task, new_id
from .storage import SQLiteStore

app = typer.Typer(no_args_is_help=True, help="Persistent AI scientist V0")


def runtime() -> tuple[Settings, SQLiteStore]:
    settings = Settings.load(Path.cwd())
    store = SQLiteStore(settings.db_path)
    store.initialize()
    return settings, store


@app.command()
def init() -> None:
    """Initialize storage and seed the NODD project."""
    settings, store = runtime()
    if store.get("nodd") is None:
        store.upsert(
            Project(
                id="nodd",
                title="Next Open Data Detector",
                status=Status.IN_PROGRESS,
                objective="Create a realistic open detector for HL-LHC tracking studies.",
                research_questions=[
                    "How does ODD material differ from modern HL-LHC trackers?",
                    "Which components dominate the discrepancy?",
                    "Which realistic component models should replace approximations?",
                    "How should layout and timing capability evolve?",
                ],
            )
        )
    typer.echo(f"Initialized {settings.db_path}")


@app.command("add-task")
def add_task(
    title: str,
    project: str | None = typer.Option(None),
    priority: str = typer.Option("medium"),
    next_action: str = typer.Option(""),
    deadline: str | None = typer.Option(None),
) -> None:
    """Add a durable task."""
    _, store = runtime()
    task = Task(
        id=new_id("TASK"),
        title=title,
        project_id=project,
        priority=priority,
        next_action=next_action,
        deadline=deadline,
    )
    store.upsert(task)
    store.audit("human", "create_task", "completed", task.id)
    typer.echo(task.id)


@app.command()
def status() -> None:
    """Print current authoritative state."""
    _, store = runtime()
    typer.echo(ContextBuilder(store).render())


@app.command()
def chat(question: str) -> None:
    """Ask the scientist using the current state snapshot."""
    settings, store = runtime()
    typer.echo(ScientistAgent(settings, store).ask(question))


if __name__ == "__main__":
    app()

