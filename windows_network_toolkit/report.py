"""Structured incident report from live state and audit trail."""

from __future__ import annotations

from typing import Any

from windows_network_toolkit.audit_store import read_audit_logs
from windows_network_toolkit.platform.risk_scoring import score_risk
from windows_network_toolkit.proof import run_diagnose_proof
from windows_network_toolkit.proxy_classification import classify_from_live
from windows_network_toolkit.proxy_owner import detect_proxy_owner
from windows_network_toolkit.proxy_state import collect_proxy_state_model
from windows_network_toolkit.safety import DEFAULT_SAFETY_NOTES


def build_proxy_report(
    *,
    url: str | None = None,
    inject: dict[str, Any] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    if inject:
        return inject

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

    return {
        "executive_summary": (
            f"Proxy classification: {classification.primary_classification} "
            f"(confidence {classification.confidence:.2f}). "
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
        "remediation_status": {
            "recommended": classification.recommended_next_actions,
            "safe_default": "preview-only proxy-disable with typed confirmation",
        },
        "risk_assessment": risk,
        "limitations": classification.limitations + proof.limitations + DEFAULT_SAFETY_NOTES[:2],
        "recommended_next_actions": classification.recommended_next_actions,
        "audit_event_count": len(audit_rows),
    }
