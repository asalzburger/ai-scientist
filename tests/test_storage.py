from pathlib import Path

from ai_scientist.domain import Project, Status, Task
from ai_scientist.storage import SQLiteStore


def test_store_round_trip(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "scientist.db")
    store.initialize()
    store.upsert(Project(id="nodd", title="NODD", status=Status.IN_PROGRESS))
    store.upsert(Task(id="TASK-1", title="Scan", project_id="nodd"))

    assert store.get("nodd")["title"] == "NODD"
    assert store.list_records(kind="task")[0]["project_id"] == "nodd"


def test_store_filters_status(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "scientist.db")
    store.initialize()
    store.upsert(Task(id="TASK-1", title="Active", status=Status.IN_PROGRESS))
    store.upsert(Task(id="TASK-2", title="Done", status=Status.DONE))

    rows = store.list_records(kind="task", statuses=["in_progress"])
    assert [row["id"] for row in rows] == ["TASK-1"]

