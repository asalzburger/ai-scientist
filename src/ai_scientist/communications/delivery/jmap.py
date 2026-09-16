"""Read-only JMAP Mail adapter using an explicitly configured API URL and account."""

import hashlib
import json
from dataclasses import dataclass, field
from email.utils import formataddr
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from ..models import MailMessage


class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


@dataclass(frozen=True)
class JMAPSettings:
    api_url: str
    account_id: str
    token: str = field(repr=False)

    def __post_init__(self):
        parsed = urlsplit(self.api_url)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.query:
            raise ValueError("JMAP requires an HTTPS API URL without credentials")


class JMAPMailbox:
    def __init__(self, settings: JMAPSettings):
        self.settings = settings

    @property
    def target(self) -> str:
        return f"jmap:{self.settings.api_url}:{self.settings.account_id}"

    def _call(self, method: str, arguments: dict) -> dict:
        if method not in {"Mailbox/get", "Email/query", "Email/get"}:
            raise PermissionError("Only read-only JMAP methods are supported")
        data = {
            "using": ["urn:ietf:params:jmap:core", "urn:ietf:params:jmap:mail"],
            "methodCalls": [[method, {"accountId": self.settings.account_id, **arguments}, "0"]],
        }
        request = Request(
            self.settings.api_url,
            data=json.dumps(data).encode(),
            headers={
                "Authorization": f"Bearer {self.settings.token}",
                "Content-Type": "application/json",
            },
        )
        with build_opener(NoRedirects()).open(request, timeout=30) as response:
            raw = response.read(5_000_001)
        if len(raw) > 5_000_000:
            raise ValueError("JMAP response exceeds 5 MB limit")
        results = json.loads(raw)["methodResponses"]
        if len(results) != 1 or results[0][0] != method or results[0][2] != "0":
            raise RuntimeError("JMAP method failed")
        return results[0][1]

    def read(self, folder: str = "INBOX", limit: int = 20) -> list[MailMessage]:
        if not 1 <= limit <= 100:
            raise ValueError("Mailbox limit must be between 1 and 100")
        mailbox_id = folder
        if folder == "INBOX":
            matches = [
                item["id"]
                for item in self._call("Mailbox/get", {})["list"]
                if item.get("role") == "inbox"
            ]
            if len(matches) != 1:
                raise ValueError("JMAP account must have exactly one inbox")
            mailbox_id = matches[0]
        ids = self._call(
            "Email/query",
            {
                "filter": {"inMailbox": mailbox_id},
                "limit": limit,
                "sort": [{"property": "receivedAt", "isAscending": False}],
            },
        )["ids"]
        if not ids:
            return []
        data = self._call(
            "Email/get",
            {
                "ids": ids,
                "fetchTextBodyValues": True,
                "maxBodyValueBytes": 100_000,
                "properties": [
                    "id",
                    "messageId",
                    "from",
                    "replyTo",
                    "to",
                    "subject",
                    "receivedAt",
                    "inReplyTo",
                    "references",
                    "textBody",
                    "bodyValues",
                ],
            },
        )

        def addresses(values):
            return ", ".join(
                formataddr((item.get("name") or "", item["email"])) for item in values or []
            )

        def refs(values):
            return tuple(f"<{value}>" for value in values or [])

        messages = []
        for item in data["list"]:
            parts = [
                item.get("bodyValues", {}).get(part["partId"], {})
                for part in item.get("textBody", [])
            ]
            body = "\n".join(
                part.get("value", "") + ("\n[Truncated]" if part.get("isTruncated") else "")
                for part in parts
            )
            messages.append(
                MailMessage(
                    id=hashlib.sha256(f"{self.target}\0{item['id']}".encode()).hexdigest(),
                    account=self.target,
                    folder=mailbox_id,
                    uid=item["id"],
                    uid_validity="jmap",
                    message_id=" ".join(refs(item.get("messageId"))),
                    sender=addresses(item.get("from")),
                    reply_to=addresses(item.get("replyTo")),
                    to=addresses(item.get("to")),
                    subject=item.get("subject", ""),
                    body=body or "[No plain-text body]",
                    date=item.get("receivedAt", ""),
                    in_reply_to=" ".join(refs(item.get("inReplyTo"))),
                    references=refs(item.get("references")),
                )
            )
        return messages
