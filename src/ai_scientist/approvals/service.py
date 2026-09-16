import hashlib
import hmac
import json
import secrets
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from ..domain import new_id
from ..policy import PolicyEngine
from ..storage import SQLiteStore
from .models import Operation


def fingerprint(payload: dict) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


class ApprovalService:
    """Human grant entry point; never expose grant() as a model tool."""

    def __init__(self, store: SQLiteStore, policy: PolicyEngine):
        self.store = store
        self.policy = policy

    def _policy(self, action: str) -> None:
        # A prompt/config change to 'autonomous' cannot remove this boundary.
        if self.policy.configuration.get("actions", {}).get(action) != "approval_required":
            raise PermissionError(f"{action} must be configured as approval_required")

    def request(self, action: str, target: str, payload: dict) -> Operation:
        self._policy(action)
        operation = Operation(
            id=new_id("OP"),
            action=action,
            target=target,
            fingerprint=fingerprint(payload),
            payload=payload,
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )
        return Operation.model_validate(
            self.store.create_operation(operation.model_dump(mode="json"))
        )

    def get(self, operation_id: str) -> Operation:
        return Operation.model_validate(self.store.operation(operation_id))

    def _current(self, operation: Operation) -> None:
        self._policy(operation.action)
        if operation.expires_at <= datetime.now(UTC):
            raise PermissionError("Approval request expired; prepare a new draft")
        if fingerprint(operation.payload) != operation.fingerprint:
            raise PermissionError("Approval payload changed")

    def grant(self, operation_id: str) -> str:
        operation = self.get(operation_id)
        self._current(operation)
        token = secrets.token_urlsafe(32)
        self.store.transition_operation(
            operation.id,
            "pending",
            "approved",
            actor="human",
            token_hash=hashlib.sha256(token.encode()).hexdigest(),
        )
        return token

    def revoke(self, operation_id: str) -> None:
        operation = self.get(operation_id)
        if operation.status not in {"pending", "approved"}:
            raise PermissionError("Only pending or unused approvals can be revoked")
        self.store.transition_operation(operation.id, operation.status, "revoked", actor="human")

    def execute(
        self,
        operation_id: str,
        token: str,
        *,
        action: str,
        target: str,
        effect: Callable[[dict], str],
    ) -> str:
        operation = self.get(operation_id)
        try:
            self._current(operation)
            if operation.action != action or operation.target != target:
                raise PermissionError("Approval does not match the action and account")
            supplied = hashlib.sha256(token.encode()).hexdigest()
            if not operation.token_hash or not hmac.compare_digest(operation.token_hash, supplied):
                raise PermissionError("Invalid approval token")
            self.store.transition_operation(
                operation.id, "approved", "executing", actor="scientist"
            )
        except PermissionError:
            self.store.audit("scientist", action, "denied", operation.id)
            raise
        try:
            receipt = effect(operation.payload)
        except Exception:
            # A server may have accepted the request before the connection failed.
            self.store.transition_operation(
                operation.id, "executing", "uncertain", actor="scientist"
            )
            raise
        self.store.transition_operation(
            operation.id, "executing", "succeeded", actor="scientist", receipt=receipt
        )
        return receipt
