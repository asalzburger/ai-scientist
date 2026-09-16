from datetime import UTC, datetime
from email.headerregistry import Address

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..domain import new_id


def header(value: str) -> str:
    if any(ord(char) < 32 or ord(char) == 127 for char in value):
        raise ValueError("Control characters are not allowed in headers")
    return value


def email_address(value: str) -> str:
    header(value)
    address = Address(addr_spec=value)
    if not address.username or not address.domain or not value.isascii():
        raise ValueError("An ASCII email address with a domain is required")
    return address.addr_spec


class EmailDraft(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    id: str = Field(default_factory=lambda: new_id("MAIL"))
    sender: str
    to: tuple[str, ...] = Field(min_length=1)
    cc: tuple[str, ...] = ()
    bcc: tuple[str, ...] = ()
    subject: str
    body: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    in_reply_to: str | None = None
    references: tuple[str, ...] = ()
    calendar_ics: str | None = None

    _sender = field_validator("sender")(email_address)
    _headers = field_validator("subject", "id")(header)

    @field_validator("to", "cc", "bcc")
    @classmethod
    def addresses(cls, values):
        return tuple(email_address(value) for value in values)

    @field_validator("created_at")
    @classmethod
    def timestamp(cls, value):
        if value.tzinfo is None:
            raise ValueError("Timestamp needs a timezone")
        return value.astimezone(UTC)

    @field_validator("in_reply_to")
    @classmethod
    def reply_header(cls, value):
        return header(value) if value is not None else None

    @field_validator("references")
    @classmethod
    def reference_headers(cls, values):
        return tuple(header(value) for value in values)

    @property
    def message_id(self) -> str:
        return f"<{self.id}@{self.sender.rsplit('@', 1)[1]}>"

    @property
    def recipients(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys((*self.to, *self.cc, *self.bcc)))


class MailMessage(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    id: str
    account: str
    folder: str
    uid: str
    uid_validity: str
    message_id: str = ""
    sender: str = ""
    reply_to: str = ""
    to: str = ""
    subject: str = ""
    body: str = ""
    date: str = ""
    in_reply_to: str = ""
    references: tuple[str, ...] = ()
