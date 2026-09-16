from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from dateutil.rrule import DAILY, MONTHLY, WEEKLY, rrule
from dateutil.tz import datetime_exists

from .models import CalendarEvent, TimeSlot


def window(start: datetime, end: datetime) -> TimeSlot:
    result = TimeSlot(start=start, end=end)
    if end - start > timedelta(days=366):
        raise ValueError("Calendar queries are limited to 366 days")
    return result


def occurrences(event: CalendarEvent, start: datetime, end: datetime) -> list[TimeSlot]:
    window(start, end)
    starts = [event.start]
    if event.recurrence:
        spec = event.recurrence
        starts = rrule(
            {"DAILY": DAILY, "WEEKLY": WEEKLY, "MONTHLY": MONTHLY}[spec.frequency],
            dtstart=event.start.astimezone(ZoneInfo(event.timezone)),
            count=spec.count,
            interval=spec.interval,
        )
    duration = event.end - event.start
    slots = []
    for occurrence in starts:
        if not datetime_exists(occurrence):
            raise ValueError("Recurrence crosses a nonexistent local time; choose another time")
        occurrence = occurrence.astimezone(UTC)
        finish = occurrence + duration
        if occurrence < end and finish > start:
            slots.append(TimeSlot(start=occurrence, end=finish))
    return slots
