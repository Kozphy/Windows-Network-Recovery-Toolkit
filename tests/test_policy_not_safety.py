"""Principle: policy ALLOW is not a safety guarantee — controls must remain enforced."""

from __future__ import annotations

import json
from pathlib import Path

from src.platform_core.principles.models import PolicyDecision
from src.platform_core.principles.rules import check_policy_not_safety
from src.platform_core.principles.validator import validate_principles

REPO = Path(__file__).resolve().parents[1]
CS1 = REPO / "case_studies" / "cs1_wininet_proxy_drift" / "fixture.json"


def test_cs1_preview_policy_passes_safety_controls() -> None:
    data = json.loads(CS1.read_text(encoding="utf-8"))
    result = validate_principles(data)
    check = next(c for c in result.checks if c.principle_id == "policy_not_safety")
    assert check.passed


def test_allow_without_confirmation_fails() -> None:
    policy = PolicyDecision(
        action="DISABLE_WININET_PROXY",
        outcome="ALLOW",
        allowed=True,
        requires_confirmation=False,
        confirmation_token="",
        dry_run=False,
        rollback_plan_present=True,
        monitoring_recommended=True,
        audit_logging=True,
    )
    check = check_policy_not_safety(policy=policy)
    assert not check.passed
    assert any("confirmation" in v.lower() for v in check.violations)


def test_allow_with_all_controls_passes() -> None:
    policy = PolicyDecision(
        action="DISABLE_WININET_PROXY",
        outcome="ALLOW",
        allowed=True,
        requires_confirmation=True,
        confirmation_token="DISABLE_WININET_PROXY",
        dry_run=True,
        rollback_plan_present=True,
        monitoring_recommended=True,
        audit_logging=True,
    )
    check = check_policy_not_safety(policy=policy)
    assert check.passed


def test_allow_missing_rollback_fails() -> None:
    policy = PolicyDecision(
        action="DISABLE_WININET_PROXY",
        outcome="ALLOW",
        allowed=True,
        requires_confirmation=True,
        confirmation_token="DISABLE_WININET_PROXY",
        dry_run=True,
        rollback_plan_present=False,
        monitoring_recommended=True,
        audit_logging=True,
    )
    check = check_policy_not_safety(policy=policy)
    assert not check.passed
    assert any("rollback" in v.lower() for v in check.violations)
