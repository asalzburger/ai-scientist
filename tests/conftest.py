import pytest

from ai_scientist.approvals.service import ApprovalService
from ai_scientist.policy import PolicyEngine
from ai_scientist.storage import SQLiteStore


@pytest.fixture
def comm_store(tmp_path):
    store = SQLiteStore(tmp_path / "communications.db")
    store.initialize()
    return store


@pytest.fixture
def approvals(comm_store):
    return ApprovalService(
        comm_store,
        PolicyEngine(
            {
                "actions": {
                    "send_email": "approval_required",
                    "modify_calendar": "approval_required",
                    "read_mailbox": "autonomous",
                    "read_calendar": "autonomous",
                }
            }
        ),
    )
