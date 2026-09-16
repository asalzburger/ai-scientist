"""Communication preferences and human feedback, independent of delivery authority."""

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..domain import new_id
from ..storage import SQLiteStore


class CommunicationPreferences(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    quick_question_channel: Literal["chat", "email"] = "chat"
    explanation_channel: Literal["chat", "email"] = "email"
    question_frequency: Literal["selective", "balanced", "frequent"] = "selective"
    batch_related_questions: bool = True
    daily_briefing_focus: Literal["forward_progress"] = "forward_progress"


class CommunicationFeedback(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    id: str = Field(default_factory=lambda: new_id("FEEDBACK"))
    dimension: Literal["frequency", "channel", "length", "clarity", "priorities", "usefulness"]
    comment: str = Field(min_length=1, max_length=4000)
    reference: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator("comment")
    @classmethod
    def nonempty(cls, value):
        if not value.strip():
            raise ValueError("Feedback must not be blank")
        return value.strip()

    @field_validator("created_at")
    @classmethod
    def utc(cls, value):
        if value.tzinfo is None:
            raise ValueError("Feedback timestamps require a timezone")
        return value.astimezone(UTC)


class FeedbackStore:
    def __init__(self, store: SQLiteStore):
        self.store = store

    def record(self, feedback: CommunicationFeedback) -> CommunicationFeedback:
        self.store.save_document(
            "communication_feedback", feedback.id, feedback.model_dump(mode="json"), actor="human"
        )
        return feedback

    def recent(self) -> list[CommunicationFeedback]:
        return [
            CommunicationFeedback.model_validate(item)
            for item in self.store.documents("communication_feedback", limit=20)
        ]
