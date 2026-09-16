from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from .domain import Record, utc_now


class SQLiteStore:
    def __init__(self, path: Path):
        self.path = path

    def connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS records (
                    id TEXT PRIMARY KEY,
                    kind TEXT NOT NULL,
                    title TEXT NOT NULL,
                    status TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS records_kind_status
                    ON records(kind, status);
                CREATE TABLE IF NOT EXISTS audit_events (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    happened_at TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    action TEXT NOT NULL,
                    target TEXT,
                    outcome TEXT NOT NULL,
                    details TEXT NOT NULL
                );
                """
            )

    def upsert(self, record: Record) -> None:
        payload = record.to_dict()
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO records(id, kind, title, status, payload, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    kind=excluded.kind,
                    title=excluded.title,
                    status=excluded.status,
                    payload=excluded.payload,
                    updated_at=excluded.updated_at
                """,
                (
                    record.id,
                    record.kind,
                    record.title,
                    record.status.value,
                    json.dumps(payload, sort_keys=True),
                    record.created_at,
                    record.updated_at,
                ),
            )

    def get(self, record_id: str) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT kind, payload FROM records WHERE id = ?", (record_id,)
            ).fetchone()
        if row is None:
            return None
        return {"kind": row["kind"], **json.loads(row["payload"])}

    def list_records(
        self, kind: str | None = None, statuses: Iterable[str] | None = None, limit: int = 100
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        parameters: list[Any] = []
        if kind:
            clauses.append("kind = ?")
            parameters.append(kind)
        status_values = list(statuses or [])
        if status_values:
            placeholders = ",".join("?" for _ in status_values)
            clauses.append(f"status IN ({placeholders})")
            parameters.extend(status_values)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        parameters.append(limit)
        with self.connect() as connection:
            rows = connection.execute(
                f"SELECT kind, payload FROM records {where} ORDER BY updated_at DESC LIMIT ?",
                parameters,
            ).fetchall()
        return [{"kind": row["kind"], **json.loads(row["payload"])} for row in rows]

    def audit(
        self,
        actor: str,
        action: str,
        outcome: str,
        target: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO audit_events(happened_at, actor, action, target, outcome, details)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (utc_now(), actor, action, target, outcome, json.dumps(details or {})),
            )
