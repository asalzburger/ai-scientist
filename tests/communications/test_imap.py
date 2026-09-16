from unittest.mock import MagicMock

from ai_scientist.communications.delivery.imap import IMAPMailbox, IMAPSettings
from ai_scientist.communications.mailbox import Mailbox


def test_imap_import_is_read_only_and_idempotent(comm_store, approvals, monkeypatch):
    factory = MagicMock()
    monkeypatch.setattr("ai_scientist.communications.delivery.imap.imaplib.IMAP4_SSL", factory)
    client = factory.return_value.__enter__.return_value
    client.login.return_value = ("OK", [])
    client.select.return_value = ("OK", [b"1"])
    client.response.return_value = ("UIDVALIDITY", [b"42"])
    raw = b"From: sender@example.org\r\nSubject: Test\r\nContent-Type: text/plain\r\n\r\nHello"

    def uid(command, *args):
        if command == "search":
            return "OK", [b"7"]
        if args[1] == "(RFC822.SIZE)":
            return "OK", [b"1 (RFC822.SIZE 100)"]
        assert args[1] == "(BODY.PEEK[])"
        return "OK", [(b"1 (BODY[])", raw)]

    client.uid.side_effect = uid
    reader = IMAPMailbox(IMAPSettings("imap.example.org", "ada", "secret"))
    service = Mailbox(comm_store, reader, approvals.policy)
    first = service.sync()
    second = service.sync()
    assert first == second
    assert len(comm_store.documents("mail_message")) == 1
    assert first[0].body == "Hello"
    client.select.assert_called_with('"INBOX"', readonly=True)
    client.store.assert_not_called()
