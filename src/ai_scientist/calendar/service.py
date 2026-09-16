"""Interface for calendar providers; CLI wiring selects the concrete adapter."""

from datetime import datetime
from typing import Protocol

from ..approvals.models import Operation
from .models import CalendarEvent, TimeSlot


class CalendarProvider(Protocol):
    @property
    def target(self) -> str: ...

    def busy(self, start: datetime, end: datetime) -> list[TimeSlot]: ...

    def request(self, event: CalendarEvent) -> Operation: ...

    def publish(self, operation_id: str, token: str) -> str: ...
