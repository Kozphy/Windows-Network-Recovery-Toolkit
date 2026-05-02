"""Stdout + unified audit payloads for Proxy Guard detection → attribution → decide → rollback."""

from __future__ import annotations

from typing import Any, Literal

from .models import ProxyGuardPolicyDecision, ProxySnapshot
from .parser import ParsedProxy

RiskLevel = Literal["low", "medium", "high"]
RecAction = Literal["none", "rollback", "prompt_user"]
RollbackVerify = Literal["passed", "failed", "not_run"]


def public_decision_label(decision: str) -> str:
    """Map internal ``observe`` branch to operator-facing ``observe_only``."""

    return "observe_only" if decision == "observe" else decision


def infer_risk_level(
    gd: ProxyGuardPolicyDecision,
    *,
    curr_snap: ProxySnapshot,
    parsed_after: ParsedProxy,
) -> RiskLevel:
    """Heuristic risk bucket for dashboards (deterministic, no external calls)."""

    if gd.decision == "allowed":
        return "low"
    if gd.decision == "observe":
        return "low"
    if parsed_after.is_localhost_proxy:
        return "high"
    if (curr_snap.proxy_enable or 0) == 1 and (curr_snap.proxy_server or "").strip():
        return "high"
    return "medium"


def infer_recommended_action(gd: ProxyGuardPolicyDecision) -> RecAction:
    """Translate guarded policy outcome into remediation hints."""

    if gd.decision == "blocked" and gd.rollback_allowed:
        return "rollback"
    if gd.decision == "blocked" and not gd.rollback_allowed:
        return "prompt_user"
    if gd.decision == "observe" and "unknown_attribution" in gd.reason:
        return "prompt_user"
    return "none"


def policy_payload_for_audit(
    gd: ProxyGuardPolicyDecision,
    *,
    curr_snap: ProxySnapshot,
    parsed_after: ParsedProxy,
) -> dict[str, Any]:
    """Unified ``policy`` subtree for pipeline JSONL."""

    return {
        "decision": public_decision_label(gd.decision),
        "reason": gd.reason,
        "matched_policy": gd.matched_rule,
        "risk_level": infer_risk_level(gd, curr_snap=curr_snap, parsed_after=parsed_after),
        "recommended_action": infer_recommended_action(gd),
    }


def rollback_payload_for_audit(
    *,
    action: str,
    restored_fields: list[str],
    verification: RollbackVerify,
    error: str | None,
) -> dict[str, Any]:
    """Unified ``rollback`` subtree matching pipeline contract."""

    return {
        "action": action,
        "restored_fields": restored_fields,
        "verification": verification,
        "error": error,
    }


def summarize_stdout_event(
    gd: ProxyGuardPolicyDecision,
    *,
    rollback_subtree: dict[str, Any],
    curr_snap: ProxySnapshot,
    parsed_after: ParsedProxy,
) -> dict[str, Any]:
    """Console JSON summary (backward-compat keys retained)."""

    pol = policy_payload_for_audit(gd, curr_snap=curr_snap, parsed_after=parsed_after)
    return {
        "decision": pol["decision"],
        "reason": pol["reason"],
        "matched_policy": pol["matched_policy"],
        "risk_level": pol["risk_level"],
        "recommended_action": pol["recommended_action"],
        "rollback": {
            "action": rollback_subtree["action"],
            "restored_fields": rollback_subtree["restored_fields"],
            "verification": rollback_subtree["verification"],
            "error": rollback_subtree["error"],
        },
        "legacy_detail": gd.reason,
    }


def disabling_transition_allowed(prior: ProxySnapshot, curr: ProxySnapshot) -> bool:
    """Return True when operator appears to disable WinINET proxy via toggle."""

    pe_b = int(prior.proxy_enable or 0)
    pe_a = int(curr.proxy_enable or 0)
    if pe_b == 1 and pe_a == 0:
        return True
    return False
