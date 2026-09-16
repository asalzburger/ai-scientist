from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:10]}"


class Status(StrEnum):
    INBOX = "inbox"
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    REVIEW = "review"
    DONE = "done"
    CANCELLED = "cancelled"


@dataclass(slots=True)
class Record:
    id: str
    title: str
    status: Status = Status.INBOX
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def kind(self) -> str:
        return type(self).__name__.lower()

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["status"] = self.status.value
        return result


@dataclass(slots=True)
class Project(Record):
    objective: str = ""
    research_questions: list[str] = field(default_factory=list)


@dataclass(slots=True)
class Task(Record):
    project_id: str | None = None
    priority: str = "medium"
    next_action: str = ""
    deadline: str | None = None
    dependencies: list[str] = field(default_factory=list)


@dataclass(slots=True)
class Experiment(Record):
    project_id: str | None = None
    question: str = ""
    hypothesis: str = ""
    baseline: str = ""
    variant: str = ""
    dataset: str = ""
    metrics: list[str] = field(default_factory=list)
    evidence_ids: list[str] = field(default_factory=list)


@dataclass(slots=True)
class Paper(Record):
    project_id: str | None = None
    venue: str = ""
    deadline: str | None = None
    claim_ids: list[str] = field(default_factory=list)


@dataclass(slots=True)
class Meeting(Record):
    starts_at: str | None = None
    participant_ids: list[str] = field(default_factory=list)
    agenda: list[str] = field(default_factory=list)
    action_ids: list[str] = field(default_factory=list)


@dataclass(slots=True)
class Person(Record):
    role: str = ""
    email: str | None = None


@dataclass(slots=True)
class Evidence(Record):
    source: str = ""
    artifact_uri: str = ""
    provenance: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class Claim(Record):
    statement: str = ""
    evidence_ids: list[str] = field(default_factory=list)
    validation: str = "unvalidated"

