from email.message import EmailMessage
from email.policy import SMTP
from email.utils import format_datetime, parseaddr

from ..storage import SQLiteStore
from .models import EmailDraft, MailMessage
from .threading import message_ids


def render(draft: EmailDraft) -> EmailMessage:
    message = EmailMessage(policy=SMTP)
    message["From"] = draft.sender
    message["To"] = ", ".join(draft.to)
    if draft.cc:
        message["Cc"] = ", ".join(draft.cc)
    message["Subject"] = draft.subject
    message["Date"] = format_datetime(draft.created_at)
    message["Message-ID"] = draft.message_id
    if draft.in_reply_to:
        message["In-Reply-To"] = draft.in_reply_to
    if draft.references:
        message["References"] = " ".join(draft.references)
    message.set_content(draft.body)
    if draft.calendar_ics:
        message.add_attachment(
            draft.calendar_ics.encode(),
            maintype="text",
            subtype="calendar",
            filename="invitation.ics",
            params={"method": "REQUEST"},
        )
    return message


class Composer:
    def __init__(self, store: SQLiteStore):
        self.store = store

    def save(self, draft: EmailDraft) -> EmailDraft:
        self.store.save_document("email_draft", draft.id, draft.model_dump(mode="json"))
        return draft

    def get(self, draft_id: str) -> EmailDraft:
        return EmailDraft.model_validate(self.store.document("email_draft", draft_id))

    def reply(self, original: MailMessage, *, sender: str, body: str) -> EmailDraft:
        _, recipient = parseaddr(original.reply_to or original.sender)
        parent = message_ids(original.message_id)
        refs = tuple(dict.fromkeys((*original.references, *parent)))
        subject = original.subject
        if not subject.lower().startswith("re:"):
            subject = "Re: " + subject
        return self.save(
            EmailDraft(
                sender=sender,
                to=(recipient,),
                subject=subject,
                body=body,
                in_reply_to=parent[0] if parent else None,
                references=refs,
            )
        )
