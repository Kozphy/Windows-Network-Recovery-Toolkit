"""Audit-ready report generator — JSON, Markdown, HTML."""

from __future__ import annotations

import json
from typing import Any, Literal

ReportFormat = Literal["json", "markdown", "html"]

_MOCK_TYPE_NAMES = frozenset(
    {"MagicMock", "Mock", "NonCallableMagicMock", "NonCallableMock", "AsyncMock"}
)


def _is_test_mock(obj: Any) -> bool:
    type_name = type(obj).__name__
    module = getattr(type(obj), "__module__", "") or ""
    return (
        type_name in _MOCK_TYPE_NAMES
        or type_name.endswith("Mock")
        or module.startswith("unittest.mock")
    )


def _json_default(obj: Any) -> str:
    """Serialize non-JSON values without leaking raw mock repr strings into reports."""
    if _is_test_mock(obj):
        return f"[non-serializable-test-mock:{type(obj).__name__}]"
    return f"[non-serializable:{type(obj).__name__}]"


def _json_dump(obj: Any) -> str:
    """Serialize audit report sections; surface test/mock objects as explicit markers."""
    return json.dumps(obj, indent=2, default=_json_default)


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
        return _json_dump(sections)
    if fmt == "html":
        body = "<h1>Endpoint Reliability Incident Report</h1>"
        body += f"<p>{sections['executive_summary']}</p>"
        body += "<h2>Timeline</h2><pre>" + _json_dump(timeline) + "</pre>"
        body += "<h2>Decision</h2><pre>" + _json_dump(decision) + "</pre>"
        return f"<!DOCTYPE html><html><body>{body}</body></html>"
    lines = [
        "# Endpoint Reliability Incident Report",
        "",
        "## 1. Executive Summary",
        sections["executive_summary"],
        "",
        "## 2. Incident Timeline",
        "```json",
        _json_dump(timeline),
        "```",
        "",
        "## 3. Evidence Collected",
        f"{len(timeline)} timeline events recorded.",
        "",
        "## 4. Hypothesis",
        _json_dump(decision.get("metadata", {})),
        "",
        "## 5. Proof",
        _json_dump(proof or []),
        "",
        "## 6. Decision",
        _json_dump(decision),
        "",
        "## 7. Risk Classification",
        str(decision.get("risk_level")),
        "",
        "## 8. Policy Gate",
        _json_dump(policy),
        "",
        "## 9. Remediation Preview",
        _json_dump(remediation),
        "",
        "## 10. Actions Taken",
        "None (preview-only run)." if policy.get("dry_run", True) else "See audit trail.",
        "",
        "## 11. Rollback Plan",
        _json_dump(remediation.get("rollback_plan", {})),
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
        _json_dump(audit_rows or []),
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
        return _json_dump(sections)
    if fmt == "html":
        body = "<h1>Endpoint Reliability Incident Report</h1>"
        body += f"<p>{sections['executive_summary']}</p>"
        for title, key in (
            ("Evidence", "evidence_collected"),
            ("Proof", "proof_results"),
            ("Policy", "policy_decision"),
            ("Timeline", "timeline"),
        ):
            body += f"<h2>{title}</h2><pre>{_json_dump(sections[key])}</pre>"
        return f"<!DOCTYPE html><html><body>{body}</body></html>"
    lines = [
        "# Endpoint Reliability Incident Report",
        "",
        "## 1. Executive Summary",
        str(sections["executive_summary"]),
        "",
        "## 2. Evidence Collected",
        "```json",
        _json_dump(sections["evidence_collected"]),
        "```",
        "",
        "## 3. Hypotheses Tested",
        _json_dump(sections["hypotheses_tested"]),
        "",
        "## 4. Proof Results",
        _json_dump(sections["proof_results"]),
        "",
        "## 5. Risk Classification",
        str(sections["risk_classification"]),
        "",
        "## 6. Policy Decision",
        _json_dump(sections["policy_decision"]),
        "",
        "## 7. Remediation Preview",
        _json_dump(sections["remediation_preview"]),
        "",
        "## 8. Approval Record",
        _json_dump(sections["approval_record"]),
        "",
        "## 9. Rollback Plan",
        _json_dump(sections["rollback_plan"]),
        "",
        "## 10. Timeline",
        "```json",
        _json_dump(sections["timeline"]),
        "```",
        "",
        "## 11. Chain of Custody",
        _json_dump(sections["chain_of_custody"]),
        "",
        "## 12. Control Mapping (informational)",
        _json_dump(sections["control_mapping"]),
        "",
        "## 13. Audit Trail",
        _json_dump(sections["audit_trail"]),
        "",
        "## 14. Safety Notes",
        "\n".join(f"- {n}" for n in sections["safety_notes"]),
    ]
    return "\n".join(lines)
