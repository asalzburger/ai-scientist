from ai_scientist.policy import Approval, Decision, PolicyEngine


def test_consequential_action_requires_matching_approval() -> None:
    policy = PolicyEngine({"default": "deny", "actions": {"send_email": "approval_required"}})
    assert policy.decision("send_email") is Decision.REQUIRE_APPROVAL
    assert policy.decision("send_email", Approval("send_email")) is Decision.ALLOW
    assert policy.decision("send_email", Approval("merge_pull_request")) is Decision.REQUIRE_APPROVAL


def test_unknown_action_is_denied() -> None:
    policy = PolicyEngine({"default": "deny", "actions": {}})
    assert policy.decision("launch_rocket") is Decision.DENY

