import pytest

from ai_scientist.communications.delivery.jmap import JMAPMailbox, JMAPSettings, NoRedirects


def test_jmap_reads_only_and_preserves_references(monkeypatch):
    reader = JMAPMailbox(JMAPSettings("https://mail.example.org/jmap", "account", "secret"))
    calls = []

    def call(method, arguments):
        calls.append(method)
        if method == "Mailbox/get":
            return {"list": [{"id": "inbox-id", "role": "inbox"}]}
        if method == "Email/query":
            assert arguments["filter"] == {"inMailbox": "inbox-id"}
            return {"ids": ["m1"]}
        return {
            "list": [
                {
                    "id": "m1",
                    "messageId": ["m1@example.org"],
                    "references": ["root@example.org"],
                    "textBody": [{"partId": "1"}],
                    "bodyValues": {"1": {"value": "Hello", "isTruncated": True}},
                }
            ]
        }

    monkeypatch.setattr(reader, "_call", call)
    result = reader.read()[0]
    assert result.message_id == "<m1@example.org>"
    assert result.references == ("<root@example.org>",)
    assert "[Truncated]" in result.body
    assert calls == ["Mailbox/get", "Email/query", "Email/get"]


def test_jmap_rejects_mutations_and_credential_redirects():
    reader = JMAPMailbox(JMAPSettings("https://mail.example.org/jmap", "account", "secret"))
    with pytest.raises(PermissionError):
        reader._call("Email/set", {})
    assert NoRedirects().redirect_request(None, None, 302, "", {}, "https://other.example") is None
