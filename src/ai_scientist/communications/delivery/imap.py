import hashlib
import imaplib
import re
import ssl
from dataclasses import dataclass, field
from email import policy
from email.parser import BytesParser

from ..models import MailMessage, header
from ..threading import message_ids


@dataclass(frozen=True)
class IMAPSettings:
    host: str
    username: str
    password: str = field(repr=False)
    port: int = 993


class IMAPMailbox:
    def __init__(self, settings: IMAPSettings):
        self.settings = settings

    @property
    def target(self) -> str:
        s = self.settings
        return f"imaps:{s.host}:{s.port}:{s.username}"

    @staticmethod
    def _ok(response):
        status, data = response
        if status != "OK":
            raise RuntimeError("IMAP command failed")
        return data

    def read(self, folder: str = "INBOX", limit: int = 20) -> list[MailMessage]:
        if not 1 <= limit <= 100:
            raise ValueError("Mailbox limit must be between 1 and 100")
        header(folder)
        if '"' in folder or "\\" in folder:
            raise ValueError("Unsupported mailbox name")
        s = self.settings
        messages = []
        with imaplib.IMAP4_SSL(
            s.host, s.port, ssl_context=ssl.create_default_context(), timeout=30
        ) as client:
            self._ok(client.login(s.username, s.password))
            self._ok(client.select(f'"{folder}"', readonly=True))
            validity = client.response("UIDVALIDITY")[1]
            if not validity or not validity[0]:
                raise RuntimeError("Server did not supply UIDVALIDITY")
            uid_validity = validity[0].decode()
            uids = self._ok(client.uid("search", None, "ALL"))[0].split()[-limit:]
            for uid in uids:
                sizes = self._ok(client.uid("fetch", uid, "(RFC822.SIZE)"))
                match = re.search(rb"RFC822.SIZE (\d+)", sizes[0])
                if not match or int(match[1]) > 1_000_000:
                    raise ValueError("Message exceeds 1 MB import limit or size is unavailable")
                data = self._ok(client.uid("fetch", uid, "(BODY.PEEK[])"))
                raw = next((item[1] for item in data if isinstance(item, tuple)), None)
                if raw is None or len(raw) > 1_000_000:
                    raise ValueError("Missing or oversized IMAP message")
                parsed = BytesParser(policy=policy.default).parsebytes(raw)
                body = parsed.get_body(preferencelist=("plain",))
                key = f"{self.target}\0{folder}\0{uid_validity}\0{uid.decode()}"
                messages.append(
                    MailMessage(
                        id=hashlib.sha256(key.encode()).hexdigest(),
                        account=self.target,
                        folder=folder,
                        uid=uid.decode(),
                        uid_validity=uid_validity,
                        message_id=str(parsed.get("Message-ID", "")),
                        sender=str(parsed.get("From", "")),
                        reply_to=str(parsed.get("Reply-To", "")),
                        to=str(parsed.get("To", "")),
                        subject=str(parsed.get("Subject", "")),
                        date=str(parsed.get("Date", "")),
                        body=body.get_content() if body else "[No plain-text body]",
                        in_reply_to=str(parsed.get("In-Reply-To", "")),
                        references=message_ids(str(parsed.get("References", ""))),
                    )
                )
        return messages
