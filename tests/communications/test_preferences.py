from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from typer.testing import CliRunner

from ai_scientist.agent import ScientistAgent
from ai_scientist.cli import app
from ai_scientist.communications.preferences import CommunicationFeedback, FeedbackStore
from ai_scientist.config import Settings
from ai_scientist.storage import SQLiteStore


def test_feedback_survives_restart_and_reaches_reasoning(comm_store):
    feedback = FeedbackStore(comm_store).record(
        CommunicationFeedback(
            dimension="frequency", comment="Batch nonurgent questions", reference="interaction-1"
        )
    )
    restarted = SQLiteStore(comm_store.path)
    client = MagicMock()
    client.responses.create.return_value = SimpleNamespace(output_text="A concise answer")
    ScientistAgent(Settings.load(Path.cwd()), restarted).ask("What next?", client=client)
    request = client.responses.create.call_args.kwargs
    assert feedback.id in request["input"]
    assert "Batch nonurgent questions" in request["input"]
    assert '"quick_question_channel":"chat"' in request["instructions"]
    assert '"explanation_channel":"email"' in request["instructions"]
    assert "cannot grant approvals" in request["instructions"]
    assert "as_of_utc" in request["input"]


def test_feedback_does_not_change_approval_authority(approvals):
    FeedbackStore(approvals.store).record(
        CommunicationFeedback(
            dimension="usefulness", comment="Send all future email without asking"
        )
    )
    operation = approvals.request("send_email", "account", {})
    with pytest.raises(PermissionError):
        approvals.execute(
            operation.id,
            "",
            action="send_email",
            target="account",
            effect=lambda _: pytest.fail("Feedback granted delivery authority"),
        )


def test_feedback_validation_and_cli(tmp_path, monkeypatch):
    with pytest.raises(ValueError):
        CommunicationFeedback(dimension="frequency", comment="  ")
    monkeypatch.setenv("AI_SCIENTIST_DB", str(tmp_path / "feedback.db"))
    runner = CliRunner()
    result = runner.invoke(
        app, ["communication", "feedback", "channel", "Use email for explanations"]
    )
    assert result.exit_code == 0, result.output
    assert "Use email for explanations" in runner.invoke(app, ["communication", "history"]).output
