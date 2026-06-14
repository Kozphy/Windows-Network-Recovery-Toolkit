"""Agent-specific RBAC — even admin cannot bypass destructive-action safety rules."""

from __future__ import annotations

from enum import StrEnum

from src.platform_core.agent.intent import AgentIntent


class AgentRole(StrEnum):
    ADMIN = "admin"
    OPERATOR = "operator"
    ANALYST = "analyst"
    VIEWER = "viewer"


def normalize_role(raw: str | None) -> AgentRole:
    value = (raw or "viewer").strip().lower()
    if value in ("admin", "operator", "analyst", "viewer"):
        return AgentRole(value)
    return AgentRole.VIEWER


_INTENT_MIN_ROLE: dict[AgentIntent, AgentRole] = {
    AgentIntent.DIAGNOSE_PROXY: AgentRole.VIEWER,
    AgentIntent.CHECK_TLS: AgentRole.ANALYST,
    AgentIntent.SCORE_WEBSITE_RISK: AgentRole.ANALYST,
    AgentIntent.GENERATE_EVIDENCE_REPORT: AgentRole.ANALYST,
    AgentIntent.PREVIEW_REMEDIATION: AgentRole.OPERATOR,
    AgentIntent.VERIFY_AUDIT_CHAIN: AgentRole.ADMIN,
    AgentIntent.UNKNOWN: AgentRole.VIEWER,
}

_ROLE_RANK = {
    AgentRole.VIEWER: 0,
    AgentRole.ANALYST: 1,
    AgentRole.OPERATOR: 2,
    AgentRole.ADMIN: 3,
}


def check_rbac(role: AgentRole, intent: AgentIntent) -> tuple[bool, str]:
    """Return (allowed, reason)."""
    required = _INTENT_MIN_ROLE.get(intent, AgentRole.VIEWER)
    if _ROLE_RANK[role] >= _ROLE_RANK[required]:
        return True, f"role {role.value} permitted for {intent.value}"
    return (
        False,
        f"role {role.value} denied for {intent.value}; requires {required.value} or higher",
    )


def can_read_agent_audit(role: AgentRole) -> bool:
    return role == AgentRole.ADMIN
