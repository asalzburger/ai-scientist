"""In-process mail protocol adapters. External writes require durable approval."""

from typing import Protocol

from ...approvals.models import Operation
from ..models import EmailDraft


class MailDelivery(Protocol):
    @property
    def target(self) -> str: ...

    def request(self, draft: EmailDraft) -> Operation: ...

    def send(self, operation_id: str, token: str) -> str: ...
