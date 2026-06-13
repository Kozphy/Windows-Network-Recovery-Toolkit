"""Structured incident report from live state and audit trail."""

from __future__ import annotations

from typing import Any

from src.platform_core.principles.report import build_principle_report_sections
from src.platform_core.principles.rules import format_confidence_display
from src.platform_core.principles.validator import build_incident_context, validate_principles

from windows_network_toolkit.audit_store import read_audit_logs
from windows_network_toolkit.platform.risk_scoring import score_risk
from windows_network_toolkit.proof import run_diagnose_proof
from windows_network_toolkit.proxy_classification import classify_from_live
from windows_network_toolkit.proxy_owner import detect_proxy_owner
from windows_network_toolkit.proxy_state import collect_proxy_state_model
from windows_network_toolkit.safety import DEFAULT_SAFETY_NOTES


def _default_policy_decision() -> dict[str, Any]:
    return {
        "action": "DISABLE_WININET_PROXY",
        "outcome": "PREVIEW_ONLY",
        "allowed": False,
        "requires_confirmation": True,
        "confirmation_token": "DISABLE_WININET_PROXY",
        "dry_run": True,
        "rollback_plan_present": True,
        "monitoring_recommended": True,
        "audit_logging": True,
        "safety_checks": [
            "no_process_kill",
            "no_firewall_reset",
            "no_adapter_disable",
            "no_winhttp_modification_unless_explicit",
        ],
    }


def build_proxy_report(
    *,
    url: str | None = None,
    inject: dict[str, Any] | None = None,
    include_principles: bool = False,
    **kwargs: Any,
) -> dict[str, Any]:
    if inject and not include_principles:
        return inject

    if inject and include_principles:
        base = dict(inject)
    else:
        base = None

    if base is None:
        state = collect_proxy_state_model(**kwargs)
        owner = detect_proxy_owner(**kwargs)
        classification = classify_from_live(**kwargs)
        proof = run_diagnose_proof(url, **kwargs)
        risk = score_risk(classification, proof)
        audit_rows = read_audit_logs()

        symptoms = []
        if state.wininet_proxy_enabled and not owner.get("listener_found") and state.localhost_port:
            symptoms.append("Browser may fail with ERR_PROXY_CONNECTION_FAILED while WinHTTP is direct.")
        if "WININET_WINHTTP_MISMATCH" in classification.secondary_signals:
            symptoms.append("WinINET and WinHTTP proxy configuration differ.")

        confidence_display = format_confidence_display(classification.confidence)
        base = {
            "executive_summary": (
                f"Proxy classification: {classification.primary_classification} "
                f"({confidence_display}). "
                f"Proof conclusion: {proof.conclusion_status}."
            ),
            "symptoms": symptoms or ["See observations — symptoms depend on application proxy usage."],
            "observations": {
                "proxy_state": state.to_dict(),
                "process_owner": owner,
            },
            "classification": classification.to_dict(),
            "evidence": classification.evidence,
            "proof_status": proof.to_dict(),
            "confidence_display": confidence_display,
            "remediation_status": {
                "recommended": classification.recommended_next_actions,
                "safe_default": "preview-only proxy-disable with typed confirmation",
            },
            "policy_decision": _default_policy_decision(),
            "dry_run": True,
            "rollback_plan_present": True,
            "monitoring_recommended": True,
            "audit_logging": True,
            "risk_assessment": risk,
            "limitations": classification.limitations + proof.limitations + DEFAULT_SAFETY_NOTES[:2],
            "recommended_next_actions": classification.recommended_next_actions,
            "audit_event_count": len(audit_rows),
        }

    if include_principles:
        validation_payload = {
            **base,
            "proof": base.get("proof_status") or base.get("proof"),
            "proxy_owner": (base.get("observations") or {}).get("process_owner"),
            "classification": base.get("classification"),
            "policy_decision": base.get("policy_decision") or _default_policy_decision(),
            "dry_run": base.get("dry_run", True),
            "rollback_plan_present": base.get("rollback_plan_present", True),
            "monitoring_recommended": base.get("monitoring_recommended", True),
            "audit_logging": base.get("audit_logging", True),
            "remediation_requested": base.get("remediation_requested", False),
        }
        compliance = validate_principles(validation_payload)
        ctx = build_incident_context(validation_payload)
        obs_dicts = [o.model_dump() for o in ctx["observations"]]
        sections = build_principle_report_sections(
            compliance=compliance,
            observations=obs_dicts,
            proof=validation_payload.get("proof") or base.get("proof_status"),
            classification=base.get("classification"),
            policy=validation_payload.get("policy_decision"),
            limitations=base.get("limitations"),
        )
        base.update(sections)
        base["confidence_display"] = compliance.confidence_display

    return base
