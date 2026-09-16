from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class Decision(StrEnum):
    ALLOW = "allow"
    REQUIRE_APPROVAL = "require_approval"
    DENY = "deny"


@dataclass(frozen=True, slots=True)
class Approval:
    action: str
    target: str | None = None


class PolicyEngine:
    def __init__(self, configuration: dict[str, Any]):
        self.configuration = configuration

    def decision(self, action: str, approval: Approval | None = None) -> Decision:
        level = self.configuration.get("actions", {}).get(
            action, self.configuration.get("default", "deny")
        )
        if level in {"autonomous", "autonomous_logged"}:
            return Decision.ALLOW
        if level == "approval_required":
            if approval is not None and approval.action == action:
                return Decision.ALLOW
            return Decision.REQUIRE_APPROVAL
        return Decision.DENY

