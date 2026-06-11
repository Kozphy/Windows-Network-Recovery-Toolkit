"""Endpoint Network Evidence & Risk orchestrator — read-only by default."""

from __future__ import annotations

import uuid
from typing import Any

from src.platform_core.attribution.writer_engine import run_proxy_writer_attribution
from src.platform_core.evidence_report.confidence_model import build_confidence_entries
from src.platform_core.evidence_report.generator import generate_evidence_report
from src.platform_core.evidence_report.timeline_merger import merge_evidence_timeline
from src.platform_core.proof.engine import run_proof_engine
from src.platform_core.tls.engine import run_tls_proof
from src.platform_core.website_risk.engine import run_website_risk

from windows_network_toolkit.diagnostics.proxy.runner import run_proxy_timeline


def run_evidence_assessment(
    url: str,
    *,
    include_tls: bool = True,
    include_website_risk: bool = True,
    inject_writer: dict[str, Any] | None = None,
    inject_proof: dict[str, Any] | None = None,
    inject_tls: dict[str, Any] | None = None,
    inject_website: dict[str, Any] | None = None,
    inject_sysmon: list[dict[str, Any]] | None = None,
    user_actions: list[dict[str, Any]] | None = None,
    run: Any = None,
    timeout: float = 20.0,
) -> dict[str, Any]:
    """Full evidence package: attribution, proof, TLS, website risk, merged timeline."""
    incident_id = f"enr-{uuid.uuid4().hex[:12]}"

    writer = run_proxy_writer_attribution(
        run=run,
        timeout=timeout,
        inject=inject_writer,
        inject_sysmon=inject_sysmon,
    )
    dead = writer.snapshot.classification.value == "DEAD_PROXY_CONFIG"
    proof = run_proof_engine(
        url,
        proxy_server=writer.snapshot.proxy_state.wininet_proxy_server or None,
        dead_localhost_proxy=dead,
        inject=inject_proof,
        run=run,
        timeout=timeout,
    )

    tls = run_tls_proof(url, inject=inject_tls, run=run, timeout=timeout) if include_tls else None
    website = (
        run_website_risk(url, inject=inject_website, run=run, timeout=timeout)
        if include_website_risk
        else None
    )

    proof_dict = proof.to_dict()
    base_timeline = run_proxy_timeline(
        url,
        inject_attribution=writer.snapshot.to_dict(),
        inject_proof=inject_proof or proof_dict,
        run=run,
        timeout=timeout,
    )

    timeline = merge_evidence_timeline(
        incident_id=incident_id,
        proxy_writer=writer.to_dict(),
        proof_results=proof.to_dict(),
        tls_proof=tls.to_dict() if tls else None,
        website_risk=website.to_dict() if website else None,
        user_actions=user_actions,
        existing_entries=base_timeline.get("timeline"),
    )

    summary_parts = [
        f"Proxy classification: {writer.classification}.",
        f"Network proof: {proof.outcome.value}.",
    ]
    if tls:
        summary_parts.append(f"TLS MITM risk: {tls.mitm_risk_level.value}.")
    if website:
        summary_parts.append(f"Website risk: {website.risk_level.value}.")

    package = {
        "incident_id": incident_id,
        "url": url,
        "executive_summary": " ".join(summary_parts),
        "proxy_writer_attribution": writer.to_dict(),
        "proof_results": proof.to_dict(),
        "tls_proof": tls.to_dict() if tls else None,
        "website_risk": website.to_dict() if website else None,
        "timeline": timeline,
        "confidence_model": [e.to_dict() for e in build_confidence_entries({})],
        "remediation_preview": base_timeline.get("remediation_preview"),
        "safety_notes": [
            "Preview-only — no silent registry modification or process termination.",
            "Evidence toolkit — not antivirus or phishing protection.",
        ],
    }
    package["confidence_model"] = [e.to_dict() for e in build_confidence_entries(package)]
    return package


def run_evidence_report(
    url: str,
    *,
    fmt: str = "markdown",
    **kwargs: Any,
) -> str:
    package = run_evidence_assessment(url, **kwargs)
    return generate_evidence_report(package, fmt=fmt)  # type: ignore[arg-type]
