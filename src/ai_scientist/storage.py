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
                CREATE TABLE IF NOT EXISTS documents (
                    kind TEXT NOT NULL,
                    id TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY(kind, id)
                );
                CREATE TABLE IF NOT EXISTS operations (
                    id TEXT PRIMARY KEY,
                    action TEXT NOT NULL,
                    target TEXT NOT NULL,
                    fingerprint TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    status TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    token_hash TEXT,
                    receipt TEXT,
                    UNIQUE(action, target, fingerprint)
                );
                """
            )

    def upsert(self, record: Record, *, actor: str = "human") -> None:
        record.updated_at = utc_now()
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
            connection.execute(
                """
                INSERT INTO audit_events(happened_at, actor, action, target, outcome, details)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    record.updated_at,
                    actor,
                    "save_record",
                    record.id,
                    "completed",
                    json.dumps({"kind": record.kind}),
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

    @staticmethod
    def _event(connection, action: str, target: str, outcome: str, actor: str) -> None:
        connection.execute(
            "INSERT INTO audit_events(happened_at, actor, action, target, outcome, details) "
            "VALUES (?, ?, ?, ?, ?, '{}')",
            (utc_now(), actor, action, target, outcome),
        )

    def save_document(
        self, kind: str, document_id: str, payload: dict, *, actor: str = "scientist"
    ) -> None:
        with self.connect() as connection:
            connection.execute(
                "INSERT INTO documents VALUES (?, ?, ?, ?) "
                "ON CONFLICT(kind, id) DO UPDATE SET payload=excluded.payload, "
                "updated_at=excluded.updated_at",
                (kind, document_id, json.dumps(payload, sort_keys=True), utc_now()),
            )
            self._event(connection, f"save_{kind}", document_id, "completed", actor)

    def document(self, kind: str, document_id: str) -> dict:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT payload FROM documents WHERE kind=? AND id=?",
                (kind, document_id),
            ).fetchone()
        if row is None:
            raise ValueError(f"Unknown {kind}: {document_id}")
        return json.loads(row["payload"])

    def documents(self, kind: str, limit: int = 100) -> list[dict]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT payload FROM documents WHERE kind=? ORDER BY updated_at DESC LIMIT ?",
                (kind, limit),
            ).fetchall()
        return [json.loads(row["payload"]) for row in rows]

    def create_operation(self, operation: dict) -> dict:
        with self.connect() as connection:
            connection.execute(
                "INSERT OR IGNORE INTO operations "
                "(id, action, target, fingerprint, payload, status, expires_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    operation["id"],
                    operation["action"],
                    operation["target"],
                    operation["fingerprint"],
                    json.dumps(operation["payload"], sort_keys=True),
                    operation["status"],
                    operation["expires_at"],
                ),
            )
            row = connection.execute(
                "SELECT * FROM operations WHERE action=? AND target=? AND fingerprint=?",
                (operation["action"], operation["target"], operation["fingerprint"]),
            ).fetchone()
            self._event(connection, operation["action"], row["id"], "requested", "scientist")
        return self._operation_row(row)

    @staticmethod
    def _operation_row(row) -> dict:
        result = dict(row)
        result["payload"] = json.loads(result["payload"])
        return result

    def operation(self, operation_id: str) -> dict:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT * FROM operations WHERE id=?", (operation_id,)
            ).fetchone()
        if row is None:
            raise ValueError(f"Unknown operation: {operation_id}")
        return self._operation_row(row)

    def operations(self, limit: int = 100) -> list[dict]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM operations ORDER BY rowid DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [self._operation_row(row) for row in rows]

    def transition_operation(
        self,
        operation_id: str,
        expected: str,
        status: str,
        *,
        actor: str,
        token_hash: str | None = None,
        receipt: str | None = None,
    ) -> None:
        with self.connect() as connection:
            cursor = connection.execute(
                "UPDATE operations SET status=?, token_hash=COALESCE(?, token_hash), receipt=? "
                "WHERE id=? AND status=? AND "
                "(? NOT IN ('approved', 'executing') OR julianday(expires_at) > julianday(?))",
                (status, token_hash, receipt, operation_id, expected, status, utc_now()),
            )
            if cursor.rowcount != 1:
                raise PermissionError(
                    "Operation expired, state changed, or approval already consumed"
                )
            self._event(connection, "operation_transition", operation_id, status, actor)
