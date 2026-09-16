from typing import Protocol

from ..policy import Decision, PolicyEngine
from ..storage import SQLiteStore
from .models import MailMessage


class MailReader(Protocol):
    @property
    def target(self) -> str: ...

    def read(self, folder: str = "INBOX", limit: int = 20) -> list[MailMessage]: ...


class Mailbox:
    def __init__(self, store: SQLiteStore, reader: MailReader, policy: PolicyEngine):
        self.store = store
        self.reader = reader
        self.policy = policy

    def sync(self, folder: str = "INBOX", limit: int = 20) -> list[MailMessage]:
        if self.policy.decision("read_mailbox") is not Decision.ALLOW:
            self.store.audit("scientist", "read_mailbox", "denied", self.reader.target)
            raise PermissionError("Mailbox reads are disabled by policy")
        self.store.audit("scientist", "read_mailbox", "started", self.reader.target)
        try:
            messages = self.reader.read(folder, limit)
            for message in messages:
                self.store.save_document(
                    "mail_message", message.id, message.model_dump(mode="json")
                )
        except Exception:
            self.store.audit("scientist", "read_mailbox", "failed", self.reader.target)
            raise
        self.store.audit("scientist", "read_mailbox", "completed", self.reader.target)
        return messages
