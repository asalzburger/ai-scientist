"""Validated local workspace operations shared by user interfaces."""

from datetime import UTC, datetime

from .domain import Note, Status, Task, new_id
from .storage import SQLiteStore


class Workspace:
    def __init__(self, store: SQLiteStore):
        self.store = store

    def _project(self, project_id: str | None) -> None:
        if project_id is not None:
            record = self.store.get(project_id)
            if record is None or record["kind"] != "project":
                raise ValueError(f"Unknown project: {project_id}")

    @staticmethod
    def _title(title: str) -> str:
        if not title.strip():
            raise ValueError("Title must not be empty")
        return title.strip()

    @staticmethod
    def _priority(priority: str) -> str:
        if priority not in {"low", "medium", "high"}:
            raise ValueError("Priority must be low, medium, or high")
        return priority

    def add_task(
        self,
        title: str,
        *,
        project_id: str | None = None,
        priority: str = "medium",
        next_action: str = "",
        deadline: str | None = None,
    ) -> Task:
        self._project(project_id)
        if deadline is not None:
            try:
                parsed = datetime.fromisoformat(deadline)
                if parsed.tzinfo is None:
                    raise ValueError("missing timezone")
                deadline = parsed.astimezone(UTC).isoformat()
            except ValueError as error:
                raise ValueError(
                    "Deadline must be an ISO 8601 timestamp with a timezone"
                ) from error
        task = Task(
            id=new_id("TASK"),
            title=self._title(title),
            project_id=project_id,
            priority=self._priority(priority),
            next_action=next_action,
            deadline=deadline,
        )
        self.store.upsert(task)
        return task

    def update_task(
        self,
        task_id: str,
        *,
        status: Status | None = None,
        next_action: str | None = None,
        priority: str | None = None,
    ) -> Task:
        record = self.store.get(task_id)
        if record is None or record["kind"] != "task":
            raise ValueError(f"Unknown task: {task_id}")
        record.pop("kind")
        record["status"] = Status(record["status"])
        task = Task(**record)
        if status is not None:
            task.status = Status(status)
        if next_action is not None:
            task.next_action = next_action
        if priority is not None:
            task.priority = self._priority(priority)
        self.store.upsert(task)
        return task

    def remember(
        self, title: str, body: str, *, category: str = "note", project_id: str | None = None
    ) -> Note:
        self._project(project_id)
        if category not in {"note", "decision"}:
            raise ValueError("Category must be note or decision")
        if not body.strip():
            raise ValueError("Note body must not be empty")
        note = Note(
            id=new_id("NOTE"),
            title=self._title(title),
            body=body.strip(),
            category=category,
            project_id=project_id,
        )
        self.store.upsert(note)
        return note
