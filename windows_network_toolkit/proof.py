"""Structured proof envelope — observation, hypothesis, proof attempts, conclusion."""

from __future__ import annotations

from typing import Any

from src.platform_core.governance.evidence_to_action import attach_governance_envelope
from src.platform_core.proof.engine import run_proof_engine
from src.platform_core.principles.report import build_principle_report_sections
from src.platform_core.principles.validator import validate_principles

from windows_network_toolkit.models import ProofAttempt, ProofResult
from windows_network_toolkit.proxy_classification import classify_from_live
from windows_network_toolkit.proxy_owner import detect_proxy_owner
from windows_network_toolkit.proxy_state import collect_proxy_state_model


def run_diagnose_proof(
    url: str | None = None,
    *,
    inject: dict[str, Any] | None = None,
    inject_proof: dict[str, Any] | None = None,
    **kwargs: Any,
) -> ProofResult:
    if inject:
        attempts = [
            ProofAttempt(**a) if isinstance(a, dict) else a
            for a in inject.get("proof_attempts", [])
        ]
        conclusion = inject.get("conclusion") or {}
        return ProofResult(
            observation=dict(inject.get("observation") or {}),
            hypothesis=str(inject.get("hypothesis") or ""),
            proof_attempts=attempts,
            conclusion_status=str(conclusion.get("status") or inject.get("conclusion_status") or ""),
            confidence=float(conclusion.get("confidence") or inject.get("confidence") or 0.0),
            limitations=list(inject.get("limitations") or []),
        )

    state = collect_proxy_state_model(**kwargs)
    owner = detect_proxy_owner(**kwargs)
    classification = classify_from_live(**kwargs)

    listener_found = bool(owner.get("listener_found"))
    observation = {
        "wininet_proxy": state.wininet_proxy_server or "none",
        "wininet_enabled": state.wininet_proxy_enabled,
        "winhttp_direct": state.winhttp_direct_access,
        "localhost_port": state.localhost_port,
        "localhost_listener": listener_found,
    }

    attempts: list[ProofAttempt] = []

    if state.localhost_port is not None:
        status = "passed" if listener_found else "failed"
        meaning = (
            f"Process listening on port {state.localhost_port}."
            if listener_found
            else "No process is listening on the configured proxy port."
        )
        attempts.append(ProofAttempt("localhost_listener_check", status, meaning))

    if state.wininet_proxy_enabled and state.winhttp_direct_access:
        attempts.append(
            ProofAttempt(
                "wininet_winhttp_comparison",
                "supported",
                "Browser proxy path differs from WinHTTP direct path.",
            )
        )

    primary = classification.primary_classification
    if primary == "DEAD_PROXY_CONFIG":
        hypothesis = "Browser failure is likely caused by dead WinINET localhost proxy."
        conclusion_status = "supported"
        confidence = 0.92 if not listener_found else 0.5
    elif primary == "WININET_WINHTTP_MISMATCH":
        hypothesis = "Browser path may fail due to WinINET/WinHTTP configuration split."
        conclusion_status = "supported"
        confidence = 0.72
    elif primary == "NO_PROXY":
        hypothesis = "Proxy misconfiguration is unlikely the root cause."
        conclusion_status = "inconclusive"
        confidence = 0.3
    else:
        hypothesis = f"Proxy state classified as {primary}; further investigation needed."
        conclusion_status = "inconclusive"
        confidence = classification.confidence

    if url:
        proof = run_proof_engine(
            url,
            proxy_server=state.wininet_proxy_server or None,
            dead_localhost_proxy=primary == "DEAD_PROXY_CONFIG",
            inject=inject_proof,
            **kwargs,
        )
        for obs in proof.observations:
            attempts.append(
                ProofAttempt(
                    name=f"{obs.probe_type}",
                    status="passed" if obs.success else "failed",
                    meaning=obs.observed_value[:200],
                )
            )
        if proof.outcome.value == "DEAD_LOCALHOST_PROXY":
            conclusion_status = "supported"
            confidence = max(confidence, 0.9)

    limitations = [
        "This does not prove malware.",
        "This does not prove MITM.",
        "This supports whether the configured proxy path is broken or unavailable.",
    ]

    return ProofResult(
        observation=observation,
        hypothesis=hypothesis,
        proof_attempts=attempts,
        conclusion_status=conclusion_status,
        confidence=confidence,
        limitations=limitations,
    )


def enrich_diagnose_payload(payload: dict[str, Any], *, include_principles: bool) -> dict[str, Any]:
    if not include_principles:
        return payload

    validation_input = {
        "proof": payload,
        "classification": {
            "confidence": (payload.get("conclusion") or {}).get("confidence", 0.0),
            "limitations": payload.get("limitations") or [],
        },
        "remediation_requested": False,
    }
    compliance = validate_principles(validation_input)
    sections = build_principle_report_sections(
        compliance=compliance,
        proof=payload,
        limitations=payload.get("limitations"),
    )
    enriched = dict(payload)
    enriched.update(
        {
            "principle_compliance": sections["principle_compliance"],
            "blocked_overclaims": sections["blocked_overclaims"],
            "evidence_chain": sections["evidence_chain"],
            "safe_remediation_controls": sections["safe_remediation_controls"],
        }
    )
    conclusion = payload.get("conclusion") or {}
    return attach_governance_envelope(
        enriched,
        proof_conclusion=conclusion.get("status") if isinstance(conclusion, dict) else None,
        dry_run=True,
        requires_confirmation=True,
    )
