"""Audit-ready report generator — JSON, Markdown, HTML."""

from __future__ import annotations

import json
from typing import Any, Literal

ReportFormat = Literal["json", "markdown", "html"]


def _executive_summary(decision: dict[str, Any], policy: dict[str, Any]) -> str:
    itype = decision.get("incident_type", "UNKNOWN")
    if itype in {"WININET_PROXY_DRIFT", "PROXY_PATH_FAIL_DIRECT_PATH_SUCCESS"}:
        return (
            "Based on the collected evidence, the endpoint exhibited symptoms of WinINET proxy drift. "
            "The browser path failed through a local loopback proxy, while the direct path succeeded. "
            "The recommended action is to disable the WinINET proxy only after explicit user confirmation. "
            "No destructive action should be performed without audit logging and rollback preparation."
        )
    return (
        f"Incident classified as {itype} with confidence {decision.get('confidence', 0):.2f}. "
        f"Policy outcome: {policy.get('outcome', 'ALLOW_PREVIEW')}. "
        "Observation is not proof; correlation is not causation."
    )


def generate_report(
    *,
    timeline: list[dict[str, Any]],
    decision: dict[str, Any],
    policy: dict[str, Any],
    remediation: dict[str, Any],
    audit_rows: list[dict[str, Any]] | None = None,
    proof: list[dict[str, Any]] | None = None,
    fmt: ReportFormat = "markdown",
) -> str:
    sections = {
        "executive_summary": _executive_summary(decision, policy),
        "incident_timeline": timeline,
        "evidence_collected": timeline,
        "hypothesis": decision.get("metadata", {}),
        "proof": proof or [],
        "decision": decision,
        "risk_classification": decision.get("risk_level"),
        "policy_gate": policy,
        "remediation_preview": remediation,
        "actions_taken": [],
        "rollback_plan": remediation.get("rollback_plan", {}),
        "audit_trail": audit_rows or [],
    }
    if fmt == "json":
        return json.dumps(sections, indent=2)
    if fmt == "html":
        body = "<h1>Endpoint Reliability Incident Report</h1>"
        body += f"<p>{sections['executive_summary']}</p>"
        body += "<h2>Timeline</h2><pre>" + json.dumps(timeline, indent=2) + "</pre>"
        body += "<h2>Decision</h2><pre>" + json.dumps(decision, indent=2) + "</pre>"
        return f"<!DOCTYPE html><html><body>{body}</body></html>"
    lines = [
        "# Endpoint Reliability Incident Report",
        "",
        "## 1. Executive Summary",
        sections["executive_summary"],
        "",
        "## 2. Incident Timeline",
        "```json",
        json.dumps(timeline, indent=2),
        "```",
        "",
        "## 3. Evidence Collected",
        f"{len(timeline)} timeline events recorded.",
        "",
        "## 4. Hypothesis",
        json.dumps(decision.get("metadata", {}), indent=2),
        "",
        "## 5. Proof",
        json.dumps(proof or [], indent=2),
        "",
        "## 6. Decision",
        json.dumps(decision, indent=2),
        "",
        "## 7. Risk Classification",
        str(decision.get("risk_level")),
        "",
        "## 8. Policy Gate",
        json.dumps(policy, indent=2),
        "",
        "## 9. Remediation Preview",
        json.dumps(remediation, indent=2),
        "",
        "## 10. Actions Taken",
        "None (preview-only run)." if policy.get("dry_run", True) else "See audit trail.",
        "",
        "## 11. Rollback Plan",
        json.dumps(remediation.get("rollback_plan", {}), indent=2),
        "",
        "## 12. Audit Trail",
        json.dumps(audit_rows or [], indent=2),
    ]
    return "\n".join(lines)
