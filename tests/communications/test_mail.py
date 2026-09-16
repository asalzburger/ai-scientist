from unittest.mock import MagicMock

import pytest

from ai_scientist.communications.composer import Composer, render
from ai_scientist.communications.delivery.smtp import SMTPDelivery, SMTPSettings
from ai_scientist.communications.models import EmailDraft, MailMessage
from ai_scientist.communications.threading import thread_key


def draft(**kwargs):
    return EmailDraft(
        sender="ada@example.org", to=("team@example.org",), subject="Update", body="Hello", **kwargs
    )


def test_header_injection_rejected():
    with pytest.raises(ValueError):
        EmailDraft(
            sender="ada@example.org",
            to=("team@example.org",),
            subject="Hello\r\nBcc: bad@example.org",
            body="Test",
        )


def test_reply_preserves_thread_and_uses_reply_to(comm_store):
    original = MailMessage(
        id="m1",
        account="a",
        folder="INBOX",
        uid="1",
        uid_validity="2",
        sender="From <from@example.org>",
        reply_to="reply@example.org",
        message_id="<child@example.org>",
        references=("<root@example.org>",),
        subject="Question",
    )
    reply = Composer(comm_store).reply(original, sender="ada@example.org", body="Answer")
    assert reply.to == ("reply@example.org",)
    assert reply.references == ("<root@example.org>", "<child@example.org>")
    assert thread_key(original) == "<root@example.org>"
    assert Composer(comm_store).get(reply.id) == reply


def test_bcc_is_envelope_only():
    message = draft(bcc=("private@example.org",))
    assert "private@example.org" in message.recipients
    assert "private@example.org" not in render(message).as_string()


def test_smtp_requires_approval_before_connecting(approvals, monkeypatch):
    factory = MagicMock()
    monkeypatch.setattr("ai_scientist.communications.delivery.smtp.smtplib.SMTP_SSL", factory)
    client = factory.return_value.__enter__.return_value
    client.send_message.return_value = {}
    delivery = SMTPDelivery(
        SMTPSettings("smtp.example.org", "ada", "secret", "ada@example.org"), approvals
    )
    message = draft(bcc=("private@example.org",))
    operation = delivery.request(message)
    with pytest.raises(PermissionError):
        delivery.send(operation.id, "invalid")
    factory.assert_not_called()
    token = approvals.grant(operation.id)
    assert delivery.send(operation.id, token) == message.message_id
    sent = client.send_message.call_args
    assert sent.kwargs["to_addrs"] == ["team@example.org", "private@example.org"]
    assert sent.args[0]["Bcc"] is None
    with pytest.raises(PermissionError):
        delivery.send(operation.id, token)
    assert client.send_message.call_count == 1


def test_partial_smtp_delivery_is_uncertain(approvals, monkeypatch):
    factory = MagicMock()
    factory.return_value.__enter__.return_value.send_message.return_value = {
        "team@example.org": (550, b"No")
    }
    monkeypatch.setattr("ai_scientist.communications.delivery.smtp.smtplib.SMTP_SSL", factory)
    delivery = SMTPDelivery(
        SMTPSettings("smtp.example.org", "ada", "secret", "ada@example.org"), approvals
    )
    operation = delivery.request(draft())
    with pytest.raises(RuntimeError):
        delivery.send(operation.id, approvals.grant(operation.id))
    assert approvals.get(operation.id).status == "uncertain"
