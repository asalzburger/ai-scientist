from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from .agent import ScientistAgent
from .communications.cli import approval, calendar, communication, contacts, guarded, mail
from .config import Settings
from .context import ContextBuilder
from .domain import Project, Status
from .storage import SQLiteStore
from .workspace import Workspace

app = typer.Typer(no_args_is_help=True, help="Persistent AI scientist V0")

app.add_typer(mail, name="mail")
app.add_typer(calendar, name="calendar")
app.add_typer(contacts, name="contacts")
app.add_typer(approval, name="approval")
app.add_typer(communication, name="communication")


def runtime() -> tuple[Settings, SQLiteStore]:
    settings = Settings.load(Path.cwd())
    store = SQLiteStore(settings.db_path)
    store.initialize()
    return settings, store


@app.command()
def init(example: bool = typer.Option(False, help="Seed the optional NODD example.")) -> None:
    """Initialize a project-neutral workspace."""
    settings, store = runtime()
    if example and store.get("nodd") is None:
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
    try:
        task = Workspace(store).add_task(
            title,
            project_id=project,
            priority=priority,
            next_action=next_action,
            deadline=deadline,
        )
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error
    typer.echo(task.id)


@app.command("update-task")
def update_task(
    task_id: str,
    status: Annotated[Status | None, typer.Option()] = None,
    next_action: str | None = typer.Option(None),
    priority: str | None = typer.Option(None),
) -> None:
    """Change a task's status, priority, or next action."""
    if status is None and next_action is None and priority is None:
        raise typer.BadParameter("Provide --status, --next-action, or --priority")
    _, store = runtime()
    try:
        task = Workspace(store).update_task(
            task_id,
            status=status,
            next_action=next_action,
            priority=priority,
        )
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error
    typer.echo(f"{task.id}: {task.status.value}")


@app.command()
def tasks(
    all: bool = typer.Option(False, "--all", help="Include completed/cancelled tasks."),
) -> None:
    """List tasks and their next actions."""
    _, store = runtime()
    records = store.list_records(kind="task", statuses=None if all else ContextBuilder.ACTIVE)
    if not records:
        typer.echo("No tasks. Add one with: ai-scientist add-task 'Your task'")
    for record in records:
        typer.echo(f"{record['id']}  [{record['status']}] [{record['priority']}] {record['title']}")
        if record["next_action"]:
            typer.echo(f"  Next: {record['next_action']}")


@app.command()
def remember(
    title: str,
    body: str,
    category: str = typer.Option("note", help="note or decision"),
    project: str | None = typer.Option(None),
) -> None:
    """Save a note or decision for future conversations."""
    _, store = runtime()
    try:
        note = Workspace(store).remember(title, body, category=category, project_id=project)
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error
    typer.echo(note.id)


@app.command()
def notes() -> None:
    """Show saved notes and decisions."""
    _, store = runtime()
    records = store.list_records(kind="note")
    if not records:
        typer.echo("No notes. Save one with: ai-scientist remember 'Title' 'Body'")
    for record in records:
        typer.echo(f"{record['id']}  [{record['category']}] {record['title']}\n{record['body']}")


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


@app.command()
def web(port: int = 8765) -> None:
    """Open a loopback-only, read-only communications review server."""
    from .web.server import serve

    _, store = runtime()
    serve(store, port)


@app.command("daily-review")
@guarded
def daily_review() -> None:
    """Draft and save today's priorities. Does not send or schedule a briefing."""
    from .scheduler.daily_review import run_daily_review

    settings, store = runtime()
    typer.echo(run_daily_review(ScientistAgent(settings, store)))


if __name__ == "__main__":
    app()
