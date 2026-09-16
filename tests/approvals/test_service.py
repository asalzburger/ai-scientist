import sqlite3
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

import pytest

from ai_scientist.approvals.service import ApprovalService


def test_exact_snapshot_and_single_use_survive_restart(approvals):
    payload = {"to": ["colleague@example.org"], "body": "Hello"}
    operation = approvals.request("send_email", "account-a", payload)
    token = approvals.grant(operation.id)
    payload["body"] = "Changed later"
    restarted = ApprovalService(approvals.store, approvals.policy)
    calls = []

    def effect(data):
        calls.append(data)
        return "receipt"

    assert (
        restarted.execute(
            operation.id, token, action="send_email", target="account-a", effect=effect
        )
        == "receipt"
    )
    assert calls == [{"to": ["colleague@example.org"], "body": "Hello"}]
    with pytest.raises(PermissionError):
        restarted.execute(
            operation.id, token, action="send_email", target="account-a", effect=effect
        )
    assert len(calls) == 1
    assert restarted.get(operation.id).status == "succeeded"


@pytest.mark.parametrize(
    "action,target,token",
    [
        ("send_email", "account-b", None),
        ("modify_calendar", "account-a", None),
        ("send_email", "account-a", "bad-token"),
    ],
)
def test_wrong_authorization_never_calls_provider(approvals, action, target, token):
    operation = approvals.request("send_email", "account-a", {"body": "Hello"})
    issued = approvals.grant(operation.id)
    with pytest.raises(PermissionError):
        approvals.execute(
            operation.id,
            token or issued,
            action=action,
            target=target,
            effect=lambda _: pytest.fail("External effect reached"),
        )


def test_pending_and_expired_approvals_block(approvals):
    operation = approvals.request("send_email", "account-a", {})
    with pytest.raises(PermissionError):
        approvals.execute(
            operation.id,
            "anything",
            action="send_email",
            target="account-a",
            effect=lambda _: pytest.fail("External effect reached"),
        )
    token = approvals.grant(operation.id)
    with approvals.store.connect() as connection:
        connection.execute(
            "UPDATE operations SET expires_at=? WHERE id=?",
            ((datetime.now(UTC) - timedelta(seconds=1)).isoformat(), operation.id),
        )
    with pytest.raises(PermissionError, match="expired"):
        approvals.execute(
            operation.id,
            token,
            action="send_email",
            target="account-a",
            effect=lambda _: pytest.fail("External effect reached"),
        )


def test_uncertain_delivery_is_not_retried(approvals):
    operation = approvals.request("send_email", "account-a", {})
    token = approvals.grant(operation.id)

    def failed(_):
        raise TimeoutError("Server may have accepted the message")

    with pytest.raises(TimeoutError):
        approvals.execute(
            operation.id, token, action="send_email", target="account-a", effect=failed
        )
    assert approvals.get(operation.id).status == "uncertain"
    assert approvals.request("send_email", "account-a", {}).id == operation.id
    with pytest.raises(PermissionError):
        approvals.grant(operation.id)


def test_concurrent_consumers_only_execute_once(approvals):
    operation = approvals.request("send_email", "account-a", {})
    token = approvals.grant(operation.id)
    calls = []

    def execute():
        try:
            approvals.execute(
                operation.id,
                token,
                action="send_email",
                target="account-a",
                effect=lambda _: calls.append(1) or "receipt",
            )
            return True
        except PermissionError:
            return False

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(lambda _: execute(), range(2))) == [False, True]
    assert calls == [1]


def test_config_cannot_remove_approval_gate(approvals):
    approvals.policy.configuration["actions"]["send_email"] = "autonomous"
    with pytest.raises(PermissionError):
        approvals.request("send_email", "account-a", {})


def test_revoked_token_cannot_execute(approvals):
    operation = approvals.request("send_email", "account-a", {})
    token = approvals.grant(operation.id)
    approvals.revoke(operation.id)
    with pytest.raises(PermissionError):
        approvals.execute(
            operation.id,
            token,
            action="send_email",
            target="account-a",
            effect=lambda _: pytest.fail("Revoked operation reached provider"),
        )


def test_failed_audit_prevents_external_effect(approvals):
    operation = approvals.request("send_email", "account-a", {})
    token = approvals.grant(operation.id)
    with approvals.store.connect() as connection:
        connection.execute("""
            CREATE TRIGGER reject_execution_audit BEFORE INSERT ON audit_events
            WHEN NEW.outcome = 'executing'
            BEGIN SELECT RAISE(ABORT, 'audit unavailable'); END
        """)
    with pytest.raises(sqlite3.IntegrityError):
        approvals.execute(
            operation.id,
            token,
            action="send_email",
            target="account-a",
            effect=lambda _: pytest.fail("Unaudited operation reached provider"),
        )
    assert approvals.get(operation.id).status == "approved"


def test_tampered_snapshot_is_rejected(approvals):
    operation = approvals.request("send_email", "account-a", {})
    token = approvals.grant(operation.id)
    with approvals.store.connect() as connection:
        connection.execute(
            "UPDATE operations SET payload=? WHERE id=?", ('{"body":"tampered"}', operation.id)
        )
    with pytest.raises(PermissionError, match="payload changed"):
        approvals.execute(
            operation.id,
            token,
            action="send_email",
            target="account-a",
            effect=lambda _: pytest.fail("External effect reached"),
        )
