from datetime import UTC, datetime
from typing import Literal
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ..communications.models import email_address
from ..domain import new_id


class Recurrence(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    frequency: Literal["DAILY", "WEEKLY", "MONTHLY"]
    count: int = Field(ge=1, le=366)
    interval: int = Field(default=1, ge=1, le=365)


class CalendarEvent(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    id: str = Field(default_factory=lambda: new_id("EVENT"))
    title: str = Field(min_length=1)
    start: datetime
    end: datetime
    timezone: str = "UTC"
    description: str = ""
    location: str = ""
    organizer: str | None = None
    attendees: tuple[str, ...] = ()
    recurrence: Recurrence | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator("start", "end", "created_at")
    @classmethod
    def utc(cls, value):
        if value.tzinfo is None:
            raise ValueError("Event timestamps need an explicit timezone")
        return value.astimezone(UTC)

    @field_validator("timezone")
    @classmethod
    def zone(cls, value):
        ZoneInfo(value)
        return value

    @field_validator("organizer")
    @classmethod
    def organizer_address(cls, value):
        return email_address(value) if value else value

    @field_validator("attendees")
    @classmethod
    def attendee_addresses(cls, values):
        return tuple(email_address(value) for value in values)

    @model_validator(mode="after")
    def ordered(self):
        if self.end <= self.start:
            raise ValueError("Event end must follow start")
        if self.attendees and not self.organizer:
            raise ValueError("Invitations need an organizer")
        return self


class TimeSlot(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    start: datetime
    end: datetime

    @field_validator("start", "end")
    @classmethod
    def utc(cls, value):
        if value.tzinfo is None:
            raise ValueError("Time slots need timezone-aware timestamps")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def valid(self):
        if self.start.tzinfo is None or self.end.tzinfo is None or self.end <= self.start:
            raise ValueError("Time slots require ordered, timezone-aware timestamps")
        return self
