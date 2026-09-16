from dataclasses import dataclass, field
from urllib.parse import quote, urlsplit

import caldav

from ..approvals.service import ApprovalService
from ..policy import Decision
from ..storage import SQLiteStore
from .invitations import busy_from_ics, to_ics
from .models import CalendarEvent
from .recurrence import window


@dataclass(frozen=True)
class CalDAVSettings:
    url: str
    username: str
    password: str = field(repr=False)
    timezone: str = "UTC"

    def __post_init__(self):
        parsed = urlsplit(self.url)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.query:
            raise ValueError("CalDAV requires an HTTPS calendar collection URL without credentials")


class CalDAVCalendar:
    def __init__(self, settings: CalDAVSettings, approvals: ApprovalService, store: SQLiteStore):
        self.settings = settings
        self.approvals = approvals
        self.store = store

    @property
    def target(self) -> str:
        return f"caldav:{self.settings.url}:{self.settings.username}"

    def _client(self):
        client = caldav.DAVClient(
            url=self.settings.url,
            username=self.settings.username,
            password=self.settings.password,
            timeout=30,
            ssl_verify_cert=True,
            rate_limit_handle=False,
        )
        client.session.max_redirects = 0
        return client

    def busy(self, start, end):
        window(start, end)
        if self.approvals.policy.decision("read_calendar") is not Decision.ALLOW:
            self.store.audit("scientist", "read_calendar", "denied", self.target)
            raise PermissionError("Calendar reads are disabled by policy")
        self.store.audit("scientist", "read_calendar", "started", self.target)
        try:
            with self._client() as client:
                calendar = client.calendar(url=self.settings.url)
                resources = calendar.search(start=start, end=end, event=True, expand=True)
                result = [
                    slot
                    for resource in resources
                    for slot in busy_from_ics(resource.data, self.settings.timezone)
                    if slot.start < end and slot.end > start
                ]
        except Exception:
            self.store.audit("scientist", "read_calendar", "failed", self.target)
            raise
        self.store.audit("scientist", "read_calendar", "completed", self.target)
        return result

    def request(self, event: CalendarEvent):
        if event.attendees:
            raise ValueError(
                "Publish personal events without attendees; send invitations via email"
            )
        return self.approvals.request("modify_calendar", self.target, event.model_dump(mode="json"))

    def publish(self, operation_id: str, token: str) -> str:
        return self.approvals.execute(
            operation_id, token, action="modify_calendar", target=self.target, effect=self._publish
        )

    def _publish(self, payload: dict) -> str:
        event = CalendarEvent.model_validate(payload)
        if event.attendees:
            raise ValueError("Server-side scheduling is not supported")
        with self._client() as client:
            url = self.settings.url.rstrip("/") + "/" + quote(event.id, safe="") + ".ics"
            response = client.put(
                url,
                to_ics(event),
                headers={"Content-Type": "text/calendar; charset=utf-8", "If-None-Match": "*"},
            )
            if response.status not in {201, 204}:
                raise RuntimeError("Calendar creation was not confirmed; inspect approval status")
            return url
