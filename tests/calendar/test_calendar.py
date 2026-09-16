from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest
from icalendar import Calendar

from ai_scientist.calendar.availability import free_slots
from ai_scientist.calendar.caldav import CalDAVCalendar, CalDAVSettings
from ai_scientist.calendar.invitations import busy_from_ics, invitation_draft, to_ics
from ai_scientist.calendar.models import CalendarEvent, Recurrence, TimeSlot
from ai_scientist.calendar.recurrence import occurrences
from ai_scientist.communications.composer import render


def event(**kwargs):
    return CalendarEvent(
        title="Planning",
        start="2026-10-19T09:00:00+02:00",
        end="2026-10-19T10:00:00+02:00",
        timezone="Europe/Zurich",
        **kwargs,
    )


def test_recurrence_keeps_local_time_across_dst():
    meeting = event(recurrence=Recurrence(frequency="WEEKLY", count=2))
    slots = occurrences(
        meeting, datetime(2026, 10, 18, tzinfo=UTC), datetime(2026, 11, 1, tzinfo=UTC)
    )
    assert [slot.start.hour for slot in slots] == [7, 8]
    assert all(slot.end - slot.start == timedelta(hours=1) for slot in slots)


def test_free_slots_merge_overlaps_and_clip_boundaries():
    start = datetime(2026, 10, 19, 8, tzinfo=UTC)
    end = start + timedelta(hours=4)
    busy = [
        TimeSlot(start=start - timedelta(hours=1), end=start + timedelta(hours=1)),
        TimeSlot(start=start + timedelta(minutes=30), end=start + timedelta(hours=2)),
        TimeSlot(start=start + timedelta(hours=3), end=end + timedelta(hours=1)),
    ]
    assert free_slots(start, end, busy) == [
        TimeSlot(start=start + timedelta(hours=2), end=start + timedelta(hours=3))
    ]


def test_invitation_is_an_unsent_mime_draft():
    meeting = event(organizer="ada@example.org", attendees=("team@example.org",))
    draft = invitation_draft(meeting)
    parsed = Calendar.from_ical(draft.calendar_ics)
    assert parsed["METHOD"] == "REQUEST"
    component = parsed.walk("VEVENT")[0]
    assert str(component["UID"]) == meeting.id
    assert str(component["ATTENDEE"]) == "mailto:team@example.org"
    assert component["ATTENDEE"].params["RSVP"] == "TRUE"
    assert render(draft).get_payload()[1].get_content_type() == "text/calendar"


def test_busy_round_trip_and_all_day_dst():
    meeting = event()
    assert busy_from_ics(to_ics(meeting)) == [TimeSlot(start=meeting.start, end=meeting.end)]
    data = (
        "BEGIN:VCALENDAR\r\nVERSION:2.0\r\nBEGIN:VEVENT\r\nUID:day\r\n"
        "DTSTART;VALUE=DATE:20261025\r\nEND:VEVENT\r\nEND:VCALENDAR\r\n"
    )
    busy = busy_from_ics(data, "Europe/Zurich")
    assert busy[0].end - busy[0].start == timedelta(hours=25)


def test_unexpanded_recurrence_fails_closed():
    with pytest.raises(ValueError, match="unexpanded"):
        busy_from_ics(to_ics(event(recurrence=Recurrence(frequency="WEEKLY", count=2))))


def test_naive_and_backwards_times_rejected():
    with pytest.raises(ValueError):
        CalendarEvent(title="Bad", start="2026-10-19T09:00:00", end="2026-10-19T10:00:00")
    with pytest.raises(ValueError):
        CalendarEvent(title="Bad", start="2026-10-19T10:00:00Z", end="2026-10-19T09:00:00Z")


def test_caldav_no_network_without_exact_approval(approvals, comm_store, monkeypatch):
    provider = CalDAVCalendar(
        CalDAVSettings("https://calendar.example.org/cal/", "ada", "secret"), approvals, comm_store
    )
    factory = MagicMock()
    monkeypatch.setattr(provider, "_client", factory)
    client = factory.return_value.__enter__.return_value
    client.put.return_value.status = 201
    meeting = event()
    operation = provider.request(meeting)
    with pytest.raises(PermissionError):
        provider.publish(operation.id, "bad")
    factory.assert_not_called()
    assert provider.publish(operation.id, approvals.grant(operation.id)).endswith(
        f"{meeting.id}.ics"
    )
    assert client.put.call_args.kwargs["headers"]["If-None-Match"] == "*"
    assert "ATTENDEE" not in client.put.call_args.args[1]


def test_caldav_read_expands_and_does_not_save(approvals, comm_store, monkeypatch):
    provider = CalDAVCalendar(
        CalDAVSettings("https://calendar.example.org/cal/", "ada", "secret"), approvals, comm_store
    )
    factory = MagicMock()
    monkeypatch.setattr(provider, "_client", factory)
    calendar = factory.return_value.__enter__.return_value.calendar.return_value
    calendar.search.return_value = [MagicMock(data=to_ics(event()))]
    start, end = event().start, event().end
    assert provider.busy(start, end) == [TimeSlot(start=start, end=end)]
    calendar.search.assert_called_once_with(start=start, end=end, event=True, expand=True)
    calendar.save_event.assert_not_called()
    factory.return_value.__enter__.return_value.put.assert_not_called()


def test_disabled_calendar_read_does_not_connect(approvals, comm_store, monkeypatch):
    approvals.policy.configuration["actions"]["read_calendar"] = "deny"
    provider = CalDAVCalendar(
        CalDAVSettings("https://calendar.example.org/cal/", "ada", "secret"), approvals, comm_store
    )
    factory = MagicMock()
    monkeypatch.setattr(provider, "_client", factory)
    with pytest.raises(PermissionError):
        provider.busy(event().start, event().end)
    factory.assert_not_called()
