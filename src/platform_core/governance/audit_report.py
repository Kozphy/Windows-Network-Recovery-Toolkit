"""Governance report built from audit directories."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.platform_core.analytics.risk_kpi import build_risk_kpi_summary, format_risk_kpi_markdown
from src.platform_core.analytics.summary import _classification_of, _load_audit_records, build_analytics_summary
from src.platform_core.controls.control_test import run_control_test_suite
from src.platform_core.governance.evidence_to_action import attach_governance_envelope
from src.platform_core.risk.business_impact import estimate_business_impact

SCHEMA_VERSION = "audit_governance_report.v1"


def _load_risk_register(path: Path | None) -> list[dict[str, Any]]:
    if path is None or not path.is_file():
        default = (
            Path(__file__).resolve().parents[3]
            / "tests"
            / "fixtures"
            / "risk_register"
            / "sample_risk_register.json"
        )
        if default.is_file():
            path = default
        else:
            return []
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return data
    return list(data.get("risks") or [])


def _dominant_classification(records: list[dict[str, Any]]) -> str | None:
    for row in records:
        cls = _classification_of(row)
        if cls:
            return cls
    return None


def _evidence_timeline(records: list[dict[str, Any]], limit: int = 20) -> list[dict[str, Any]]:
    timeline = []
    for row in sorted(records, key=lambda r: str(r.get("timestamp") or ""))[:limit]:
        timeline.append(
            {
                "timestamp": row.get("timestamp"),
                "incident_id": row.get("incident_id") or row.get("case_id"),
                "event": row.get("action") or row.get("command") or "observation",
                "classification": _classification_of(row),
            }
        )
    return timeline


def build_audit_governance_report(
    audit_dir: Path,
    *,
    risk_register_path: Path | None = None,
    format: str = "json",
) -> str | dict[str, Any]:
    records, files, _ = _load_audit_records(audit_dir)
    kpi_payload = build_risk_kpi_summary(audit_dir)
    analytics = build_analytics_summary(audit_dir)
    control_tests = run_control_test_suite(audit_records=records)
    risk_register = _load_risk_register(risk_register_path)
    dominant_cls = _dominant_classification(records)
    business_impact = estimate_business_impact(classification=dominant_cls)

    integrity = kpi_payload.get("audit_integrity") or {}
    chain_ok = integrity.get("hash_chain_invalid_count", 0) == 0

    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "command": "governance-report",
        "executive_summary": (
            "Audit-backed governance report for technology risk review. "
            "Supports evidence-backed assessment and policy-gated remediation preview — "
            "not malware detection or autonomous remediation."
        ),
        "incident_overview": {
            "total_incidents": kpi_payload["kpis"]["total_incidents"],
            "unresolved": kpi_payload["kpis"]["unresolved_incident_count"],
            "high_residual_risk": kpi_payload["kpis"]["high_residual_risk_count"],
        },
        "evidence_timeline": _evidence_timeline(records),
        "evidence_tier_explanation": {
            "observation": "Registry/proxy snapshot — not proof.",
            "correlation": "Listener/process correlation — not writer causation.",
            "proof": "Structured proof checks passed — still not malware verdict.",
        },
        "risk_register_summary": risk_register,
        "control_test_results": [t.model_dump() for t in control_tests],
        "policy_decisions": kpi_payload["kpis"].get("policy_decisions_by_type", {}),
        "remediation_previews": {
            "count": kpi_payload["kpis"].get("remediation_previews_count", 0),
            "confirmed_executions": kpi_payload["kpis"].get("confirmed_remediations_count", 0),
        },
        "business_impact_estimate": business_impact.model_dump(),
        "analytics_summary": analytics.get("counts"),
        "risk_kpis": kpi_payload.get("kpis"),
        "audit_chain_verification": {
            "verified": chain_ok,
            "details": integrity,
        },
        "limitations": list(kpi_payload.get("limitations") or [])
        + business_impact.limitations
        + [
            "Governance report aggregates audit JSONL — does not replace formal audit opinion.",
            "MITRE ATT&CK references are triage context only, not attribution.",
        ],
        "recommended_next_actions": [
            "Review unresolved high-residual incidents with evidence tier context.",
            "Run control-test suite on case fixtures for design effectiveness.",
            "Keep remediation preview-only until typed confirmation and rollback plan.",
            "Export KPIs to warehouse for trend dashboards.",
        ],
        "source": {
            "audit_dir": str(audit_dir.resolve()),
            "files": [p.name for p in files],
        },
    }
    payload = attach_governance_envelope(payload, dry_run=True, requires_confirmation=True)

    if format == "json":
        return payload

    md = _format_markdown(payload, kpi_payload)
    if format == "html":
        return _markdown_to_html(md)
    return md


def _format_markdown(payload: dict[str, Any], kpi_payload: dict[str, Any]) -> str:
    kpi_md = format_risk_kpi_markdown(kpi_payload)
    lines = [
        "# Technology Risk Governance Report (Audit-Backed)",
        "",
        "## Executive Summary",
        "",
        payload["executive_summary"],
        "",
        kpi_md,
        "",
        "## Control Test Results",
        "",
    ]
    for test in payload.get("control_test_results") or []:
        lines.append(f"- **{test['control_id']}** ({test['result']}): {test['control_objective']}")
    lines.extend(["", "## Business Impact Estimate (Ordinal)", ""])
    bi = payload.get("business_impact_estimate") or {}
    lines.append(f"- Total business impact score: **{bi.get('total_business_impact_score')}** (ordinal, not probability)")
    lines.append(f"- Downtime minutes (estimate): {bi.get('downtime_minutes')}")
    lines.append(f"- Affected users (estimate): {bi.get('affected_users')}")
    lines.extend(["", "## Audit Chain Verification", ""])
    chain = payload.get("audit_chain_verification") or {}
    lines.append(f"- Verified: **{chain.get('verified')}**")
    lines.extend(["", "## Limitations", ""])
    for lim in payload.get("limitations") or []:
        lines.append(f"- {lim}")
    lines.extend(["", "## Recommended Next Actions", ""])
    for action in payload.get("recommended_next_actions") or []:
        lines.append(f"- {action}")
    return "\n".join(lines)


def _markdown_to_html(markdown: str) -> str:
    body = markdown.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    body = body.replace("\n\n", "</p><p>").replace("\n", "<br/>")
    return (
        "<!DOCTYPE html><html><head><meta charset='utf-8'/>"
        "<title>Technology Risk Governance Report</title></head>"
        f"<body><p>{body}</p></body></html>"
    )
