import sqlite3

import pytest

from ai_scientist.context import ContextBuilder
from ai_scientist.domain import Project, Status
from ai_scientist.storage import SQLiteStore
from ai_scientist.workspace import Workspace


@pytest.fixture
def store(tmp_path):
    result = SQLiteStore(tmp_path / "workspace.db")
    result.initialize()
    return result


def test_task_lifecycle_survives_restart(store):
    task = Workspace(store).add_task("Try the scientist", next_action="Read the instructions")
    restarted = SQLiteStore(store.path)
    Workspace(restarted).update_task(task.id, status=Status.DONE, next_action="")
    saved = restarted.get(task.id)
    assert saved["status"] == "done"
    assert saved["created_at"] == task.created_at
    assert saved["next_action"] == ""
    assert ContextBuilder(restarted).snapshot()["active_tasks"] == []
    with restarted.connect() as connection:
        events = connection.execute("SELECT action, target FROM audit_events").fetchall()
    assert [(row["action"], row["target"]) for row in events] == [
        ("save_record", task.id),
        ("save_record", task.id),
    ]


def test_notes_and_decisions_reappear_in_context(store):
    note = Workspace(store).remember("Focus", "Make the scientist usable", category="decision")
    snapshot = ContextBuilder(SQLiteStore(store.path)).snapshot()
    assert snapshot["notes_and_decisions"][0]["id"] == note.id
    assert snapshot["notes_and_decisions"][0]["body"] == "Make the scientist usable"


@pytest.mark.parametrize(
    "kwargs",
    [
        {"title": " "},
        {"title": "Task", "priority": "urgent"},
        {"title": "Task", "project_id": "missing"},
        {"title": "Task", "deadline": "2026-09-16"},
    ],
)
def test_invalid_task_does_not_mutate_storage(store, kwargs):
    with pytest.raises(ValueError):
        Workspace(store).add_task(**kwargs)
    assert store.list_records() == []


def test_deadline_normalized_to_utc(store):
    task = Workspace(store).add_task("Task", deadline="2026-09-16T12:00:00+02:00")
    assert task.deadline == "2026-09-16T10:00:00+00:00"


def test_cannot_update_project_as_task(store):
    store.upsert(Project(id="project", title="Project"))
    with pytest.raises(ValueError, match="Unknown task"):
        Workspace(store).update_task("project", status=Status.DONE)
    assert store.get("project")["status"] == "inbox"


def test_audit_failure_rolls_back_record(store):
    with store.connect() as connection:
        connection.execute("""
            CREATE TRIGGER reject_audit BEFORE INSERT ON audit_events
            BEGIN SELECT RAISE(ABORT, 'audit unavailable'); END
        """)
    with pytest.raises(sqlite3.IntegrityError):
        Workspace(store).add_task("Must not persist without audit")
    assert store.list_records() == []
