from pathlib import Path

from typer.testing import CliRunner

from ai_scientist.agent import ScientistAgent
from ai_scientist.cli import app
from ai_scientist.config import Settings
from ai_scientist.domain import Task
from ai_scientist.scheduler.daily_review import run_daily_review
from ai_scientist.storage import SQLiteStore
from ai_scientist.web.api import ReviewAPI


def test_daily_review_saves_draft_without_changing_tasks(comm_store, monkeypatch):
    comm_store.upsert(Task(id="task-1", title="Unblock work"))
    observed = []

    def ask(self, question):
        observed.append(question)
        return "1. Clarify the blocking input for task-1 so implementation can proceed."

    monkeypatch.setattr(ScientistAgent, "ask", ask)
    output = run_daily_review(ScientistAgent(Settings.load(Path.cwd()), comm_store))
    restarted = SQLiteStore(comm_store.path)
    saved = restarted.documents("daily_briefing")[0]
    assert saved["status"] == "draft"
    assert saved["body"] == output
    assert restarted.get("task-1")["status"] == "inbox"
    assert restarted.operations() == []
    assert "move work forward" in observed[0]
    assert ReviewAPI(restarted).get("/api/briefings")[0]["id"] == saved["id"]


def test_daily_review_cli(tmp_path, monkeypatch):
    monkeypatch.setenv("AI_SCIENTIST_DB", str(tmp_path / "briefings.db"))
    monkeypatch.setattr(ScientistAgent, "ask", lambda self, question: "No active work is recorded.")
    result = CliRunner().invoke(app, ["daily-review"])
    assert result.exit_code == 0, result.output
    assert "No active work" in result.output
