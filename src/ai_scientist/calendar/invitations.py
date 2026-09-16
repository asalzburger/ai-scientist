from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from icalendar import Calendar, Event, vCalAddress

from ..communications.models import EmailDraft
from .models import CalendarEvent, TimeSlot


def to_ics(event: CalendarEvent, *, invitation: bool = False) -> str:
    calendar = Calendar()
    calendar.add("prodid", "-//AI Scientist//Communications//EN")
    calendar.add("version", "2.0")
    if invitation:
        if not event.organizer or not event.attendees:
            raise ValueError("Invitation requires organizer and attendees")
        calendar.add("method", "REQUEST")
    component = Event()
    component.add("uid", event.id)
    component.add("dtstamp", event.created_at)
    component.add("sequence", 0)
    zone = ZoneInfo(event.timezone)
    component.add("dtstart", event.start.astimezone(zone))
    component.add("dtend", event.end.astimezone(zone))
    component.add("summary", event.title)
    component.add("description", event.description)
    component.add("location", event.location)
    if event.recurrence:
        component.add(
            "rrule",
            {
                "freq": event.recurrence.frequency,
                "count": event.recurrence.count,
                "interval": event.recurrence.interval,
            },
        )
    if invitation:
        component.add("organizer", vCalAddress(f"mailto:{event.organizer}"))
        for address in event.attendees:
            component.add(
                "attendee",
                vCalAddress(f"mailto:{address}"),
                parameters={"RSVP": "TRUE", "PARTSTAT": "NEEDS-ACTION"},
            )
    calendar.add_component(component)
    # Include timezone definitions so recipients need not guess timezone rules.
    calendar.add_missing_timezones()
    return calendar.to_ical().decode()


def invitation_draft(event: CalendarEvent) -> EmailDraft:
    ics = to_ics(event, invitation=True)
    zone = ZoneInfo(event.timezone)
    return EmailDraft(
        sender=event.organizer,
        to=event.attendees,
        subject=event.title,
        body=f"{event.title}\n{event.start.astimezone(zone).isoformat()} – "
        f"{event.end.astimezone(zone).isoformat()}\n{event.location}\n\n"
        f"{event.description}",
        calendar_ics=ics,
    )


def busy_from_ics(data: str, timezone: str = "UTC") -> list[TimeSlot]:
    """Parse server-expanded instances. Fail closed if expansion is incomplete."""
    zone = ZoneInfo(timezone)

    def aware(value):
        if isinstance(value, datetime):
            return (value if value.tzinfo else value.replace(tzinfo=zone)).astimezone(UTC)
        if isinstance(value, date):
            return datetime.combine(value, time.min, zone).astimezone(UTC)
        raise ValueError("Unsupported calendar date")

    slots = []
    for component in Calendar.from_ical(data).walk("VEVENT"):
        if component.get("status") == "CANCELLED" or component.get("transp") == "TRANSPARENT":
            continue
        if any(key in component for key in ("RRULE", "RDATE", "EXDATE")):
            raise ValueError("Server returned unexpanded recurrence; availability is unknown")
        original = component.decoded("dtstart")
        start = aware(original)
        if "dtend" in component:
            end = aware(component.decoded("dtend"))
        elif "duration" in component:
            end = start + component.decoded("duration")
        elif not isinstance(original, datetime):
            end = aware(original + timedelta(days=1))
        else:
            # A VEVENT with DTSTART only has zero duration.
            continue
        slots.append(TimeSlot(start=start, end=end))
    return slots
