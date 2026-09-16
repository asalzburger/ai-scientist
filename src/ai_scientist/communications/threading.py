import re

from .models import MailMessage


def message_ids(value: str) -> tuple[str, ...]:
    return tuple(dict.fromkeys(re.findall(r"<[^<>\s]+>", value)))


def thread_key(message: MailMessage) -> str:
    """Use RFC message references, never subject-only grouping."""
    ids = message.references or message_ids(message.in_reply_to) or message_ids(message.message_id)
    return ids[0] if ids else message.id
