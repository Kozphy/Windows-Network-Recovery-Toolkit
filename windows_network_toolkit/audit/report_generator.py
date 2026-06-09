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
        "## 12. Residual Risk",
        "Policy permission is not a safety guarantee. Correlation is not causation.",
        "",
        "## 13. Control Mapping (informational)",
        "| Gate | ITGC-style |",
        "|------|------------|",
        f"| {policy.get('outcome', 'PREVIEW_ONLY')} | Detect / Audit / Prevent |",
        "",
        "## 14. Audit Trail",
        json.dumps(audit_rows or [], indent=2),
    ]
    return "\n".join(lines)


def generate_erp_report(package: dict[str, Any], *, fmt: ReportFormat = "markdown") -> str:
    """Generate full ERP audit report from run_full_incident_report output."""
    sections = {
        "executive_summary": package.get("executive_summary", ""),
        "evidence_collected": package.get("evidence_collected", []),
        "hypotheses_tested": package.get("hypotheses_tested", []),
        "proof_results": package.get("proof_results", {}),
        "risk_classification": package.get("risk_classification"),
        "policy_decision": package.get("policy_gate", {}),
        "remediation_preview": package.get("remediation_preview", {}),
        "approval_record": package.get("approval_record", {}),
        "rollback_plan": package.get("rollback_plan", {}),
        "timeline": package.get("timeline", []),
        "chain_of_custody": package.get("chain_of_custody", []),
        "control_mapping": package.get("control_mapping", []),
        "audit_trail": package.get("audit_trail", []),
        "decision": package.get("decision", {}),
        "safety_notes": package.get("safety_notes", []),
    }
    if fmt == "json":
        return json.dumps(sections, indent=2)
    if fmt == "html":
        body = "<h1>Endpoint Reliability Incident Report</h1>"
        body += f"<p>{sections['executive_summary']}</p>"
        for title, key in (
            ("Evidence", "evidence_collected"),
            ("Proof", "proof_results"),
            ("Policy", "policy_decision"),
            ("Timeline", "timeline"),
        ):
            body += f"<h2>{title}</h2><pre>{json.dumps(sections[key], indent=2)}</pre>"
        return f"<!DOCTYPE html><html><body>{body}</body></html>"
    lines = [
        "# Endpoint Reliability Incident Report",
        "",
        "## 1. Executive Summary",
        str(sections["executive_summary"]),
        "",
        "## 2. Evidence Collected",
        "```json",
        json.dumps(sections["evidence_collected"], indent=2),
        "```",
        "",
        "## 3. Hypotheses Tested",
        json.dumps(sections["hypotheses_tested"], indent=2),
        "",
        "## 4. Proof Results",
        json.dumps(sections["proof_results"], indent=2),
        "",
        "## 5. Risk Classification",
        str(sections["risk_classification"]),
        "",
        "## 6. Policy Decision",
        json.dumps(sections["policy_decision"], indent=2),
        "",
        "## 7. Remediation Preview",
        json.dumps(sections["remediation_preview"], indent=2),
        "",
        "## 8. Approval Record",
        json.dumps(sections["approval_record"], indent=2),
        "",
        "## 9. Rollback Plan",
        json.dumps(sections["rollback_plan"], indent=2),
        "",
        "## 10. Timeline",
        "```json",
        json.dumps(sections["timeline"], indent=2),
        "```",
        "",
        "## 11. Chain of Custody",
        json.dumps(sections["chain_of_custody"], indent=2),
        "",
        "## 12. Control Mapping (informational)",
        json.dumps(sections["control_mapping"], indent=2),
        "",
        "## 13. Audit Trail",
        json.dumps(sections["audit_trail"], indent=2),
        "",
        "## 14. Safety Notes",
        "\n".join(f"- {n}" for n in sections["safety_notes"]),
    ]
    return "\n".join(lines)
