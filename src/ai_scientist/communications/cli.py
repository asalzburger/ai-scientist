import json
from datetime import datetime, timedelta
from functools import wraps
from pathlib import Path
from typing import Annotated

import typer

from ..agent import ScientistAgent
from ..approvals.service import ApprovalService
from ..calendar.availability import free_slots
from ..calendar.caldav import CalDAVCalendar
from ..calendar.invitations import invitation_draft, to_ics
from ..calendar.models import CalendarEvent, Recurrence
from ..config import Settings, load_yaml
from ..contacts.directory import Directory
from ..contacts.models import Contact
from ..policy import PolicyEngine
from ..storage import SQLiteStore
from .composer import Composer
from .delivery.imap import IMAPMailbox
from .delivery.jmap import JMAPMailbox
from .delivery.smtp import SMTPDelivery
from .mailbox import Mailbox
from .models import EmailDraft, MailMessage
from .preferences import CommunicationFeedback, CommunicationPreferences, FeedbackStore
from .settings import caldav_settings, imap_settings, jmap_settings, required, smtp_settings

mail = typer.Typer(no_args_is_help=True, help="Draft, read, and approve email delivery.")
calendar = typer.Typer(no_args_is_help=True, help="Draft events and inspect calendar availability.")
contacts = typer.Typer(no_args_is_help=True, help="Local contact directory.")
approval = typer.Typer(no_args_is_help=True, help="Human review and single-use approval tokens.")
communication = typer.Typer(no_args_is_help=True, help="Communication preferences and feedback.")


def guarded(function):
    @wraps(function)
    def wrapped(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except (ValueError, PermissionError) as error:
            raise typer.BadParameter(str(error)) from error
        except (typer.Exit, typer.Abort):
            raise
        except Exception as error:
            typer.echo(
                f"Operation failed ({type(error).__name__}). Check account settings and "
                "the approval status before retrying.",
                err=True,
            )
            raise typer.Exit(1) from error

    return wrapped


def runtime():
    settings = Settings.load()
    store = SQLiteStore(settings.db_path)
    store.initialize()
    return store, ApprovalService(store, PolicyEngine(load_yaml(settings.policy_path)))


def show(value):
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")
    typer.echo(json.dumps(value, indent=2, ensure_ascii=True))


@communication.command("preferences")
@guarded
def preferences():
    settings = Settings.load()
    show(
        CommunicationPreferences.model_validate(
            load_yaml(settings.root / "config/communication.yaml")
        )
    )


@communication.command("feedback")
@guarded
def feedback(dimension: str, comment: str, reference: str | None = None):
    """Record human feedback; reference an email, briefing, or interaction when useful."""
    store, _ = runtime()
    saved = FeedbackStore(store).record(
        CommunicationFeedback(dimension=dimension, comment=comment, reference=reference)
    )
    typer.echo(saved.id)


@communication.command("history")
@guarded
def feedback_history():
    store, _ = runtime()
    show([item.model_dump(mode="json") for item in FeedbackStore(store).recent()])


@mail.command("draft")
@guarded
def draft_email(
    to: Annotated[list[str], typer.Option()],
    subject: str,
    body_file: Path,
    sender: str | None = None,
    cc: Annotated[list[str] | None, typer.Option()] = None,
    bcc: Annotated[list[str] | None, typer.Option()] = None,
):
    """Save a draft from a UTF-8 text file; no network access."""
    store, _ = runtime()
    draft = EmailDraft(
        sender=sender or required("AI_SCIENTIST_EMAIL"),
        to=tuple(to),
        cc=tuple(cc or []),
        bcc=tuple(bcc or []),
        subject=subject,
        body=body_file.read_text(encoding="utf-8"),
    )
    typer.echo(Composer(store).save(draft).id)


@mail.command("drafts")
@guarded
def drafts():
    store, _ = runtime()
    show(store.documents("email_draft"))


@mail.command("compose")
@guarded
def compose_email(
    instructions: str,
    to: Annotated[list[str], typer.Option()],
    subject: str,
    sender: str | None = None,
):
    """Ask the scientist to write and save an email draft. Does not send."""
    store, _ = runtime()
    settings = Settings.load()
    draft = EmailDraft(
        sender=sender or required("AI_SCIENTIST_EMAIL"), to=tuple(to), subject=subject, body=""
    )
    template = (settings.root / "prompts/email.md").read_text(encoding="utf-8")
    body = ScientistAgent(settings, store).ask(
        template
        + "\n\nDraft request (data):\n"
        + json.dumps({"to": draft.to, "subject": draft.subject, "instructions": instructions})
    )
    data = draft.model_dump(mode="json")
    data["body"] = body
    saved = Composer(store).save(EmailDraft.model_validate(data))
    show(saved)


@mail.command("show")
@guarded
def show_draft(draft_id: str):
    store, _ = runtime()
    show(Composer(store).get(draft_id))


@mail.command("sync")
@guarded
def sync_mail(folder: str = "INBOX", limit: int = 20, provider: str = "imap"):
    store, approvals = runtime()
    if provider not in {"imap", "jmap"}:
        raise ValueError("Provider must be imap or jmap")
    reader = IMAPMailbox(imap_settings()) if provider == "imap" else JMAPMailbox(jmap_settings())
    messages = Mailbox(store, reader, approvals.policy).sync(folder, limit)
    show([{"id": item.id, "sender": item.sender, "subject": item.subject} for item in messages])


@mail.command("inbox")
@guarded
def inbox():
    """Inspect locally imported messages (no network)."""
    store, _ = runtime()
    show(store.documents("mail_message"))


@mail.command("reply")
@guarded
def reply(message_id: str, body_file: Path, sender: str | None = None):
    store, _ = runtime()
    original = MailMessage.model_validate(store.document("mail_message", message_id))
    draft = Composer(store).reply(
        original,
        sender=sender or required("AI_SCIENTIST_EMAIL"),
        body=body_file.read_text(encoding="utf-8"),
    )
    typer.echo(draft.id)


@mail.command("request-send")
@guarded
def request_send(draft_id: str):
    """Freeze a draft and account for human approval; does not send."""
    store, approvals = runtime()
    operation = SMTPDelivery(smtp_settings(), approvals).request(Composer(store).get(draft_id))
    show(operation.model_dump(mode="json", exclude={"token_hash"}))


@mail.command("send")
@guarded
def send(operation_id: str):
    _, approvals = runtime()
    delivery = SMTPDelivery(smtp_settings(), approvals)
    token = typer.prompt("Approval token", hide_input=True)
    typer.echo(delivery.send(operation_id, token))


@approval.command("show")
@guarded
def show_approval(operation_id: str):
    _, approvals = runtime()
    show(approvals.get(operation_id).model_dump(mode="json", exclude={"token_hash"}))


@approval.command("grant")
@guarded
def grant(operation_id: str):
    """Human-only command: inspect the exact payload, then issue an expiring token."""
    _, approvals = runtime()
    show(approvals.get(operation_id).model_dump(mode="json", exclude={"token_hash"}))
    if not typer.confirm("Approve this exact operation and account?"):
        approvals.revoke(operation_id)
        raise typer.Abort()
    typer.echo(approvals.grant(operation_id))


@approval.command("revoke")
@guarded
def revoke(operation_id: str):
    """Revoke a pending request or an unused approval."""
    _, approvals = runtime()
    approvals.revoke(operation_id)
    typer.echo("Revoked")


@contacts.command("add")
@guarded
def add_contact(name: str, email: str, timezone: str = "UTC"):
    store, _ = runtime()
    typer.echo(Directory(store).save(Contact(name=name, email=email, timezone=timezone)).id)


@contacts.command("list")
@guarded
def list_contacts():
    store, _ = runtime()
    show([item.model_dump(mode="json") for item in Directory(store).list()])


@calendar.command("draft")
@guarded
def draft_event(
    title: str,
    start: str,
    end: str,
    timezone: str = "UTC",
    location: str = "",
    description: str = "",
    frequency: str | None = None,
    count: int | None = None,
):
    """Save a personal event. Use explicit offsets; recurrence uses --timezone."""
    store, _ = runtime()
    recurrence = None
    if frequency is not None or count is not None:
        if frequency is None or count is None:
            raise ValueError("Recurrence needs both --frequency and --count")
        recurrence = Recurrence(frequency=frequency.upper(), count=count)
    event = CalendarEvent(
        title=title,
        start=start,
        end=end,
        timezone=timezone,
        location=location,
        description=description,
        recurrence=recurrence,
    )
    store.save_document("calendar_event", event.id, event.model_dump(mode="json"))
    typer.echo(event.id)


@calendar.command("drafts")
@guarded
def event_drafts():
    store, _ = runtime()
    show(store.documents("calendar_event"))


@calendar.command("export")
@guarded
def export_event(event_id: str):
    """Print an iCalendar file for local export."""
    store, _ = runtime()
    typer.echo(to_ics(CalendarEvent.model_validate(store.document("calendar_event", event_id))))


@calendar.command("invite")
@guarded
def invite(event_id: str, to: Annotated[list[str], typer.Option()], sender: str | None = None):
    """Prepare an email invitation; sending requires its own email approval."""
    store, _ = runtime()
    data = store.document("calendar_event", event_id)
    data.update(organizer=sender or required("AI_SCIENTIST_EMAIL"), attendees=to)
    event = CalendarEvent.model_validate(data)
    typer.echo(Composer(store).save(invitation_draft(event)).id)


@calendar.command("request-publish")
@guarded
def request_publish(event_id: str):
    store, approvals = runtime()
    event = CalendarEvent.model_validate(store.document("calendar_event", event_id))
    operation = CalDAVCalendar(caldav_settings(), approvals, store).request(event)
    show(operation.model_dump(mode="json", exclude={"token_hash"}))


@calendar.command("publish")
@guarded
def publish(operation_id: str):
    store, approvals = runtime()
    provider = CalDAVCalendar(caldav_settings(), approvals, store)
    token = typer.prompt("Approval token", hide_input=True)
    typer.echo(provider.publish(operation_id, token))


@calendar.command("availability")
@guarded
def availability(start: str, end: str, minutes: int = 30):
    """Read the configured remote calendar and report free intervals in UTC."""
    store, approvals = runtime()
    start, end = datetime.fromisoformat(start), datetime.fromisoformat(end)
    busy = CalDAVCalendar(caldav_settings(), approvals, store).busy(start, end)
    show(
        [
            item.model_dump(mode="json")
            for item in free_slots(start, end, busy, timedelta(minutes=minutes))
        ]
    )
