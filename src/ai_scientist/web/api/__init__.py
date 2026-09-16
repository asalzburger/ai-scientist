from ...storage import SQLiteStore


class ReviewAPI:
    """Read-only views. Approval issuance is deliberately absent from this API."""

    def __init__(self, store: SQLiteStore):
        self.store = store

    def get(self, path: str):
        kinds = {
            "/api/briefings": "daily_briefing",
            "/api/drafts": "email_draft",
            "/api/mail": "mail_message",
            "/api/calendar": "calendar_event",
            "/api/contacts": "contact",
        }
        if path in kinds:
            return self.store.documents(kinds[path])
        if path == "/api/approvals":
            return [
                {key: value for key, value in row.items() if key != "token_hash"}
                for row in self.store.operations()
            ]
        raise KeyError(path)
