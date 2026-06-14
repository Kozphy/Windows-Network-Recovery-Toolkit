"""Agent RBAC tests."""

from __future__ import annotations

from src.platform_core.agent.intent import AgentIntent
from src.platform_core.agent.rbac import AgentRole, check_rbac, normalize_role


def test_viewer_can_diagnose_proxy() -> None:
    ok, _ = check_rbac(AgentRole.VIEWER, AgentIntent.DIAGNOSE_PROXY)
    assert ok


def test_viewer_cannot_preview_remediation() -> None:
    ok, reason = check_rbac(AgentRole.VIEWER, AgentIntent.PREVIEW_REMEDIATION)
    assert not ok
    assert "operator" in reason


def test_operator_can_preview_remediation() -> None:
    ok, _ = check_rbac(AgentRole.OPERATOR, AgentIntent.PREVIEW_REMEDIATION)
    assert ok


def test_only_admin_can_verify_audit_chain() -> None:
    assert not check_rbac(AgentRole.OPERATOR, AgentIntent.VERIFY_AUDIT_CHAIN)[0]
    assert check_rbac(AgentRole.ADMIN, AgentIntent.VERIFY_AUDIT_CHAIN)[0]


def test_normalize_role_defaults_viewer() -> None:
    assert normalize_role(None) == AgentRole.VIEWER
    assert normalize_role("invalid") == AgentRole.VIEWER
