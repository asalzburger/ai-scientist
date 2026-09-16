from typer.testing import CliRunner

from ai_scientist.cli import app

runner = CliRunner()


def test_project_neutral_workflow(tmp_path, monkeypatch):
    monkeypatch.setenv("AI_SCIENTIST_DB", str(tmp_path / "workspace.db"))
    assert runner.invoke(app, ["init"]).exit_code == 0
    assert '"projects": []' in runner.invoke(app, ["status"]).output
    result = runner.invoke(app, ["add-task", "Try the scientist"])
    assert result.exit_code == 0, result.output
    task_id = result.output.strip()
    assert "Try the scientist" in runner.invoke(app, ["tasks"]).output
    result = runner.invoke(app, ["update-task", task_id, "--status", "done"])
    assert result.exit_code == 0, result.output
    assert "Try the scientist" not in runner.invoke(app, ["tasks"]).output
    assert "Try the scientist" in runner.invoke(app, ["tasks", "--all"]).output
    result = runner.invoke(app, ["remember", "Focus", "Usability", "--category", "decision"])
    assert result.exit_code == 0, result.output
    assert "Usability" in runner.invoke(app, ["notes"]).output
    assert "Usability" in runner.invoke(app, ["status"]).output


def test_example_initialization_is_optional_and_idempotent(tmp_path, monkeypatch):
    monkeypatch.setenv("AI_SCIENTIST_DB", str(tmp_path / "workspace.db"))
    for _ in range(2):
        assert runner.invoke(app, ["init", "--example"]).exit_code == 0
    assert runner.invoke(app, ["status"]).output.count('"id": "nodd"') == 1


def test_invalid_update_reports_error(tmp_path, monkeypatch):
    monkeypatch.setenv("AI_SCIENTIST_DB", str(tmp_path / "workspace.db"))
    result = runner.invoke(app, ["update-task", "missing", "--status", "done"])
    assert result.exit_code == 2
    assert "Unknown task" in result.output
