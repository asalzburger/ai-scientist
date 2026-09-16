import json

from typer.testing import CliRunner

from ai_scientist.cli import app

runner = CliRunner()


def test_offline_draft_and_calendar_workflow(tmp_path, monkeypatch):
    monkeypatch.setenv("AI_SCIENTIST_DB", str(tmp_path / "communications.db"))
    body = tmp_path / "body.txt"
    body.write_text("Can we meet next week?", encoding="utf-8")
    result = runner.invoke(
        app,
        [
            "mail",
            "draft",
            "--to",
            "team@example.org",
            "Planning",
            str(body),
            "--sender",
            "ada@example.org",
        ],
    )
    assert result.exit_code == 0, result.output
    draft_id = result.output.strip()
    assert "Can we meet" in runner.invoke(app, ["mail", "show", draft_id]).output
    result = runner.invoke(
        app,
        [
            "calendar",
            "draft",
            "Planning",
            "2026-10-19T09:00:00+02:00",
            "2026-10-19T10:00:00+02:00",
            "--timezone",
            "Europe/Zurich",
        ],
    )
    assert result.exit_code == 0, result.output
    event_id = result.output.strip()
    assert "BEGIN:VEVENT" in runner.invoke(app, ["calendar", "export", event_id]).output
    result = runner.invoke(
        app,
        ["calendar", "invite", event_id, "--to", "team@example.org", "--sender", "ada@example.org"],
    )
    assert result.exit_code == 0, result.output
    assert "METHOD:REQUEST" in runner.invoke(app, ["mail", "show", result.output.strip()]).output


def test_model_composes_durable_draft_only(tmp_path, monkeypatch):
    monkeypatch.setenv("AI_SCIENTIST_DB", str(tmp_path / "communications.db"))
    monkeypatch.setattr(
        "ai_scientist.communications.cli.ScientistAgent.ask",
        lambda self, question: "Hello, could we arrange a meeting?",
    )
    result = runner.invoke(
        app,
        [
            "mail",
            "compose",
            "Arrange a meeting",
            "--to",
            "team@example.org",
            "Planning",
            "--sender",
            "ada@example.org",
        ],
    )
    assert result.exit_code == 0, result.output
    saved = json.loads(result.output)
    assert saved["body"] == "Hello, could we arrange a meeting?"
    assert saved["id"] in runner.invoke(app, ["mail", "drafts"]).output


def test_grant_requires_human_confirmation(tmp_path, monkeypatch, approvals):
    monkeypatch.setenv("AI_SCIENTIST_DB", str(approvals.store.path))
    operation = approvals.request("send_email", "account-a", {"body": "Hello"})
    result = runner.invoke(app, ["approval", "grant", operation.id], input="n\n")
    assert result.exit_code != 0
    assert approvals.get(operation.id).status == "revoked"
