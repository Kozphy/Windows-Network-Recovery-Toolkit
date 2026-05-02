"""Policy engine — which remediations are allowed from which surface and at what risk tier."""

from __future__ import annotations

import re
import uuid
from typing import Any, Literal

from pydantic import BaseModel, Field

from .models import (
    FailureEvent,
    RemediationPolicy,
    RemediationPreview,
    RequestSurface,
    utc_now_iso,
)

RiskName = Literal["read_only", "low", "medium", "high", "forbidden"]

# Map conceptual action keys to risk + allowlist script basename (under scripts/).
ACTION_REGISTRY: dict[str, dict[str, Any]] = {
    "inspect_proxy": {"risk": "read_only", "script": None, "phrase": ""},
    "preview_dns_flush": {"risk": "read_only", "script": None, "phrase": ""},
    "reset_dns": {"risk": "medium", "script": "reset_dns.bat", "phrase": "RUN_DNS_RESET"},
    "reset_proxy": {"risk": "medium", "script": "reset_proxy.bat", "phrase": "RUN_PROXY_RESET"},
    "reset_firewall": {"risk": "high", "script": "reset_firewall.bat", "phrase": "RUN_FIREWALL_RESET"},
    "arbitrary_command": {"risk": "forbidden", "script": None, "phrase": ""},
}

DEFAULT_POLICY = RemediationPolicy()


class PolicyDecision(BaseModel):
    """Serializable policy outcome."""

    allowed: bool
    reason: str
    effective_risk: RiskName = "read_only"


def require_typed_confirmation(action_name: str) -> str:
    """Return required phrase for action or empty if none."""
    meta = ACTION_REGISTRY.get(action_name, {})
    return str(meta.get("phrase") or "")


def evaluate_action(
    action_name: str,
    risk_level: RiskName,
    requested_surface: RequestSurface,
    policy: RemediationPolicy | None = None,
) -> PolicyDecision:
    """Decide whether an action may proceed under policy and surface rules."""
    pol = policy or DEFAULT_POLICY
    if action_name == "arbitrary_command" or risk_level == "forbidden":
        return PolicyDecision(allowed=False, reason="forbidden_action", effective_risk="forbidden")
    if risk_level == "high":
        return PolicyDecision(allowed=False, reason="high_risk_blocked_from_platform", effective_risk="high")
    if requested_surface == "api" and not pol.can_run_from_api:
        return PolicyDecision(allowed=False, reason="api_disabled_by_policy", effective_risk=risk_level)
    if requested_surface == "cli" and not pol.can_run_from_cli:
        return PolicyDecision(allowed=False, reason="cli_disabled_by_policy", effective_risk=risk_level)
    if risk_level not in pol.allowed_risk_levels:
        return PolicyDecision(allowed=False, reason="risk_level_not_allowed", effective_risk=risk_level)
    if action_name in pol.forbidden_actions:
        return PolicyDecision(allowed=False, reason="action_forbidden_by_policy", effective_risk=risk_level)
    return PolicyDecision(allowed=True, reason="ok", effective_risk=risk_level)


def build_preview(
    failure_event: FailureEvent,
    recommended_action: str,
    *,
    requested_surface: RequestSurface = "api",
    policy: RemediationPolicy | None = None,
) -> RemediationPreview:
    """Build a RemediationPreview from a failure event and recommended action key."""
    pol = policy or DEFAULT_POLICY
    meta = ACTION_REGISTRY.get(recommended_action, {"risk": "medium", "script": None, "phrase": ""})
    risk = meta.get("risk", "medium")
    if risk not in ("read_only", "low", "medium", "high", "forbidden"):
        risk = "medium"
    phrase = str(meta.get("phrase") or "")
    commands: list[str] = []
    script = meta.get("script")
    if script:
        commands.append(f"scripts\\\\{script}  (allowlisted)")
    pd = evaluate_action(recommended_action, risk, requested_surface, pol)
    needs_confirm = pol.requires_confirmation and risk in ("low", "medium")
    return RemediationPreview(
        preview_id=str(uuid.uuid4()),
        endpoint_id=failure_event.endpoint_id,
        failure_event_id=failure_event.event_id,
        proposed_action=recommended_action,
        risk_level=risk,
        rationale=failure_event.summary or "See FailureBlock / event linkage.",
        commands_preview=commands,
        rollback_plan="Follow FailureBlock rollback_plan or toolkit docs; prototype does not auto-rollback.",
        requires_typed_confirmation=needs_confirm and bool(phrase),
        confirmation_phrase=phrase,
        allowed_by_policy=pd.allowed,
        policy_reason=pd.reason,
        created_at=utc_now_iso(),
    )


def validate_confirmation_phrase(action_name: str, phrase: str) -> bool:
    """Constant-time-safe enough for portfolio: exact match of required phrase."""
    expected = require_typed_confirmation(action_name)
    if not expected:
        return True
    return phrase.strip() == expected


def is_shell_injection(text: str) -> bool:
    """Reject obvious injection patterns in user-supplied fields."""
    if re.search(r"[;&|`$]", text):
        return True
    if "\n" in text or "\r" in text:
        return True
    return False
