"""Unified proxy diagnostic orchestrator — ties attribution, proof, timeline, remediation."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from src.platform_core.attribution.collector import (
    attribution_to_evidence_records,
    collect_attribution,
)
from src.platform_core.proof.engine import run_proof_engine
from src.platform_core.proof.models import ProofOutcome
from src.platform_core.remediation.planner import plan_proxy_drift_remediation
from src.platform_core.timeline.builder import IncidentTimelineBuilder
from src.platform_core.timeline.models import TimelineEntry
from src.platform_core.audit.writer import append_audit


def _now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def run_proxy_status(*, inject: dict[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
    snap = collect_attribution(inject=inject, **kwargs)
    ps = snap.proxy_state
    return {
        "timestamp_utc": snap.timestamp_utc,
        "wininet": {
            "ProxyEnable": ps.wininet_proxy_enable,
            "ProxyServer": ps.wininet_proxy_server,
            "ProxyOverride": ps.wininet_proxy_override,
            "AutoConfigURL": ps.wininet_auto_config_url,
        },
        "winhttp": {
            "direct_access": ps.winhttp_direct_access,
            "raw_excerpt": ps.winhttp_raw[:400],
        },
        "localhost_port": ps.localhost_port,
        "classification": snap.classification.value,
    }


def run_proxy_attribution(*, inject: dict[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
    snap = collect_attribution(inject=inject, **kwargs)
    return snap.to_dict()


def run_proxy_proof(
    url: str,
    *,
    inject: dict[str, Any] | None = None,
    inject_attribution: dict[str, Any] | None = None,
    inject_proof: dict[str, Any] | None = None,
    run: Any = None,
    timeout: float = 15.0,
) -> dict[str, Any]:
    attr = collect_attribution(inject=inject_attribution, run=run, timeout=timeout)
    dead = attr.classification.value == "DEAD_PROXY_CONFIG"
    proof = run_proof_engine(
        url,
        proxy_server=attr.proxy_state.wininet_proxy_server or None,
        dead_localhost_proxy=dead,
        inject=inject_proof or inject,
        run=run,
        timeout=timeout,
    )
    return proof.to_dict()


def run_proxy_timeline(
    url: str | None = None,
    *,
    inject_attribution: dict[str, Any] | None = None,
    inject_proof: dict[str, Any] | None = None,
    run: Any = None,
    timeout: float = 15.0,
) -> dict[str, Any]:
    incident_id = f"inc-{uuid.uuid4().hex[:12]}"
    builder = IncidentTimelineBuilder(incident_id=incident_id)
    attr = collect_attribution(inject=inject_attribution, run=run, timeout=timeout)
    builder.add_proxy_state(attr)
    records = attribution_to_evidence_records(attr, event_id=incident_id)
    builder.add_evidence_records(records)
    if url:
        dead = attr.classification.value == "DEAD_PROXY_CONFIG"
        proof = run_proof_engine(
            url,
            proxy_server=attr.proxy_state.wininet_proxy_server or None,
            dead_localhost_proxy=dead,
            inject=inject_proof,
            run=run,
            timeout=timeout,
        )
        builder.add_proof_result(proof)
    signals = {
        "wininet_proxy_enabled": attr.proxy_state.wininet_proxy_enable == 1,
        "proxy_server_localhost": "127.0.0.1" in attr.proxy_state.wininet_proxy_server,
        "listener_on_proxy_port": attr.listener.pid is not None,
        "incident_type": "WININET_PROXY_DRIFT",
        "evidence_tier": "CORRELATED" if attr.listener.pid else "OBSERVED_ONLY",
    }
    remediation = plan_proxy_drift_remediation(
        incident_id=incident_id,
        signals=signals,
        prior_proxy_enable=attr.proxy_state.wininet_proxy_enable,
        prior_proxy_server=attr.proxy_state.wininet_proxy_server,
        dry_run=True,
    )
    builder.add_remediation_preview(remediation)
    return {
        "incident_id": incident_id,
        "timeline": builder.build(),
        "attribution": attr.to_dict(),
        "remediation_preview": remediation,
    }


def run_full_incident_report(
    url: str,
    *,
    audit_path: str | None = None,
    inject_attribution: dict[str, Any] | None = None,
    inject_proof: dict[str, Any] | None = None,
    run: Any = None,
    timeout: float = 15.0,
) -> dict[str, Any]:
    """Build audit-ready incident package for report generation."""
    timeline_data = run_proxy_timeline(
        url,
        inject_attribution=inject_attribution,
        inject_proof=inject_proof,
        run=run,
        timeout=timeout,
    )
    incident_id = timeline_data["incident_id"]
    attr = timeline_data["attribution"]
    remediation = timeline_data["remediation_preview"]
    proof = run_proxy_proof(
        url,
        inject_attribution=attr,
        inject_proof=inject_proof,
        run=run,
        timeout=timeout,
    )

    decision = remediation["decision"]
    policy = remediation["policy_gate"]
    chain_of_custody = [
        {
            "evidence_id": r.evidence_id,
            "integrity_hash": r.chain_of_custody.integrity_hash,
        }
        for r in attribution_to_evidence_records(
            collect_attribution(inject=attr),
            event_id=incident_id,
        )
    ]

    audit_row: dict[str, Any] | None = None
    if audit_path:
        from pathlib import Path

        record = append_audit(
            "remediation_previewed",
            incident_id=incident_id,
            decision_id=str(decision.get("decision_id", "")),
            payload={"url": url, "policy_outcome": policy.get("outcome")},
            path=Path(audit_path),
        )
        audit_row = record.model_dump(mode="json")
        if audit_row:
            builder = IncidentTimelineBuilder(incident_id=incident_id)
            for entry in timeline_data["timeline"]:
                builder.add_entry(TimelineEntry.model_validate(entry))
            builder.add_audit_record(audit_row)
            timeline_data["timeline"] = builder.build()

    from src.platform_core.governance.control_mapping import map_policy_outcome_to_controls

    return {
        "incident_id": incident_id,
        "url": url,
        "executive_summary": (
            f"Proxy diagnostic for {url}. Classification: {attr.get('classification')}. "
            f"Proof outcome: {proof.get('outcome')}. Policy: {policy.get('outcome')}."
        ),
        "timeline": timeline_data["timeline"],
        "evidence_collected": chain_of_custody,
        "hypotheses_tested": [
            {"hypothesis": "WININET_PROXY_DRIFT", "proof_outcome": proof.get("outcome")},
            {"hypothesis": "DEAD_LOCALHOST_PROXY", "classification": attr.get("classification")},
        ],
        "proof_results": proof,
        "decision": decision,
        "risk_classification": decision.get("risk_level"),
        "policy_gate": policy,
        "remediation_preview": remediation,
        "approval_record": remediation.get("approval"),
        "rollback_plan": remediation.get("rollback_plan"),
        "chain_of_custody": chain_of_custody,
        "control_mapping": map_policy_outcome_to_controls(str(policy.get("outcome", "PREVIEW_ONLY"))),
        "audit_trail": [audit_row] if audit_row else [],
        "safety_notes": remediation.get("safety_notes", []),
    }
