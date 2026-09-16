import smtplib
import ssl
from dataclasses import dataclass, field
from typing import Literal

from ...approvals.service import ApprovalService
from ..composer import render
from ..models import EmailDraft, email_address


@dataclass(frozen=True)
class SMTPSettings:
    host: str
    username: str
    password: str = field(repr=False)
    sender: str
    port: int = 465
    security: Literal["tls", "starttls"] = "tls"

    def __post_init__(self):
        email_address(self.sender)
        if not self.host or not self.username or not self.password:
            raise ValueError("SMTP host, username, and password are required")
        if self.security not in {"tls", "starttls"}:
            raise ValueError("SMTP requires TLS or STARTTLS")


class SMTPDelivery:
    def __init__(self, settings: SMTPSettings, approvals: ApprovalService):
        self.settings = settings
        self.approvals = approvals

    @property
    def target(self) -> str:
        s = self.settings
        return f"smtp:{s.security}:{s.host}:{s.port}:{s.username}:{s.sender}"

    def request(self, draft: EmailDraft):
        if draft.sender != self.settings.sender:
            raise ValueError("Draft sender must match configured SMTP sender")
        return self.approvals.request("send_email", self.target, draft.model_dump(mode="json"))

    def send(self, operation_id: str, token: str) -> str:
        return self.approvals.execute(
            operation_id, token, action="send_email", target=self.target, effect=self._send
        )

    def _send(self, payload: dict) -> str:
        draft = EmailDraft.model_validate(payload)
        if draft.sender != self.settings.sender:
            raise ValueError("Sender does not match configured account")
        s = self.settings
        context = ssl.create_default_context()
        if s.security == "tls":
            connection = smtplib.SMTP_SSL(s.host, s.port, timeout=30, context=context)
        else:
            connection = smtplib.SMTP(s.host, s.port, timeout=30)
        with connection as client:
            if s.security == "starttls":
                client.ehlo()
                client.starttls(context=context)
                client.ehlo()
            client.login(s.username, s.password)
            refused = client.send_message(
                render(draft), from_addr=draft.sender, to_addrs=list(draft.recipients)
            )
            if refused:
                raise RuntimeError("Some recipients were refused; inspect server before retrying")
        return draft.message_id
