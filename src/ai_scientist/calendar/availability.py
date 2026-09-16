from datetime import timedelta

from .models import TimeSlot
from .recurrence import window


def free_slots(start, end, busy: list[TimeSlot], minimum: timedelta = timedelta(minutes=30)):
    """Subtract overlapping busy intervals within an explicitly supplied window."""
    window(start, end)
    if minimum <= timedelta(0):
        raise ValueError("Minimum duration must be positive")
    cursor = start
    result = []
    for interval in sorted(busy, key=lambda item: item.start):
        if interval.end <= start or interval.start >= end:
            continue
        left, right = max(start, interval.start), min(end, interval.end)
        if left - cursor >= minimum:
            result.append(TimeSlot(start=cursor, end=left))
        cursor = max(cursor, right)
    if end - cursor >= minimum:
        result.append(TimeSlot(start=cursor, end=end))
    return result
