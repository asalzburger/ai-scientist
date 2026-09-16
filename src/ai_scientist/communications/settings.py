"""Explicit account configuration from environment variables; no secret persistence."""

import os

from ..calendar.caldav import CalDAVSettings
from .delivery.imap import IMAPSettings
from .delivery.jmap import JMAPSettings
from .delivery.smtp import SMTPSettings


def required(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ValueError(f"Set {name} before connecting this account")
    return value


def smtp_settings() -> SMTPSettings:
    return SMTPSettings(
        host=required("AI_SCIENTIST_SMTP_HOST"),
        username=required("AI_SCIENTIST_SMTP_USERNAME"),
        password=required("AI_SCIENTIST_SMTP_PASSWORD"),
        sender=required("AI_SCIENTIST_EMAIL"),
        port=int(os.getenv("AI_SCIENTIST_SMTP_PORT", "465")),
        security=os.getenv("AI_SCIENTIST_SMTP_SECURITY", "tls"),
    )


def imap_settings() -> IMAPSettings:
    return IMAPSettings(
        host=required("AI_SCIENTIST_IMAP_HOST"),
        username=required("AI_SCIENTIST_IMAP_USERNAME"),
        password=required("AI_SCIENTIST_IMAP_PASSWORD"),
        port=int(os.getenv("AI_SCIENTIST_IMAP_PORT", "993")),
    )


def caldav_settings() -> CalDAVSettings:
    return CalDAVSettings(
        url=required("AI_SCIENTIST_CALDAV_URL"),
        username=required("AI_SCIENTIST_CALDAV_USERNAME"),
        password=required("AI_SCIENTIST_CALDAV_PASSWORD"),
        timezone=os.getenv("AI_SCIENTIST_CALDAV_TIMEZONE", "UTC"),
    )


def jmap_settings() -> JMAPSettings:
    return JMAPSettings(
        api_url=required("AI_SCIENTIST_JMAP_URL"),
        account_id=required("AI_SCIENTIST_JMAP_ACCOUNT_ID"),
        token=required("AI_SCIENTIST_JMAP_TOKEN"),
    )
