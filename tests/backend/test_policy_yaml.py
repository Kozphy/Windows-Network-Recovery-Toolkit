"""Policy-as-code YAML evaluator tests."""

from __future__ import annotations

from backend.services.policy_yaml import evaluate_yaml_policy, load_policy_yaml


def test_load_default_policy():
    doc = load_policy_yaml()
    assert doc.get("schema_version") == "enterprise_policy.v1"
    assert doc.get("safety", {}).get("default_mode") == "read_only"


def test_suspicious_proxy_requires_human_approval():
    ev = evaluate_yaml_policy("SUSPICIOUS_PROXY")
    assert ev.requires_human_approval is True
    assert ev.severity == "CRITICAL"


def test_kill_process_blocked_by_safety():
    ev = evaluate_yaml_policy("UNKNOWN_LOCAL_PROXY", requested_action="kill_process")
    assert "kill_process" in ev.blocked_actions
