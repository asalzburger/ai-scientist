from __future__ import annotations

import json
from typing import Any

from .storage import SQLiteStore


class ContextBuilder:
    ACTIVE = ("inbox", "planned", "in_progress", "blocked", "review")

    def __init__(self, store: SQLiteStore):
        self.store = store

    def snapshot(self) -> dict[str, Any]:
        return {
            "projects": self.store.list_records(kind="project", limit=20),
            "active_tasks": self.store.list_records(
                kind="task", statuses=self.ACTIVE, limit=50
            ),
            "active_experiments": self.store.list_records(
                kind="experiment", statuses=self.ACTIVE, limit=20
            ),
            "papers": self.store.list_records(kind="paper", statuses=self.ACTIVE, limit=20),
            "upcoming_meetings": self.store.list_records(
                kind="meeting", statuses=self.ACTIVE, limit=20
            ),
        }

    def render(self) -> str:
        return json.dumps(self.snapshot(), indent=2, sort_keys=True)

