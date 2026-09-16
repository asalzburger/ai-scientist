from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..policy import Approval, Decision, PolicyEngine
from ..storage import SQLiteStore


@dataclass(frozen=True, slots=True)
class CodexJob:
    repository: Path
    outcome: str
    constraints: tuple[str, ...]
    acceptance_tests: tuple[str, ...]
    write: bool = False

    def prompt(self) -> str:
        constraints = "\n".join(f"- {item}" for item in self.constraints)
        tests = "\n".join(f"- {item}" for item in self.acceptance_tests)
        return (
            f"Outcome:\n{self.outcome}\n\nConstraints:\n{constraints}"
            f"\n\nAcceptance tests:\n{tests}"
        )


class CodexDelegate:
    """Policy gate and job representation; SDK execution is intentionally V1 work."""

    def __init__(self, policy: PolicyEngine, store: SQLiteStore):
        self.policy = policy
        self.store = store

    def authorize(self, job: CodexJob, approval: Approval | None = None) -> Decision:
        action = "delegate_codex_workspace_write" if job.write else "read_repository"
        decision = self.policy.decision(action, approval)
        self.store.audit(
            actor="scientist",
            action=action,
            target=str(job.repository.resolve()),
            outcome=decision.value,
            details={"outcome": job.outcome},
        )
        return decision

