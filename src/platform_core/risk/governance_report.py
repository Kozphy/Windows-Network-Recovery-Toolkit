"""Governance decision and management reporting."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from .asset import asset_for_fixture
from .business_objective import objective_for_fixture
from .control import controls_for_fixture
from .control_test import run_control_tests
from .finding import findings_from_fixture
from .risk_rating import rate_risk
from .threat import threat_for_fixture


class GovernanceDecision(BaseModel):
    decision_id: str
    outcome: str
    dry_run: bool = True
    requires_typed_confirmation: bool = True
    rollback_plan_required: bool = True
    audit_logging_required: bool = True
    recommended_action: str
    governance_owner: str = "IT Governance"
    limitations: list[str] = Field(default_factory=list)


def load_fixture(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _governance_decision(fixture: dict[str, Any]) -> GovernanceDecision:
    policy = fixture.get("policy_decision") or {}
    dry_run = bool(fixture.get("dry_run", True) or policy.get("dry_run", True))
    outcome = policy.get("outcome", "PREVIEW_ONLY")
    classification = (fixture.get("classification") or {}).get("primary_classification", "")
    action = policy.get("action") or f"Preview remediation for {classification}"
    return GovernanceDecision(
        decision_id="GOV_001",
        outcome=outcome,
        dry_run=dry_run,
        requires_typed_confirmation=bool(policy.get("requires_confirmation", True)),
        rollback_plan_required=bool(fixture.get("rollback_plan_present", True)),
        audit_logging_required=bool(policy.get("audit_logging", True)),
        recommended_action=action,
        governance_owner="IT Operations / IT Governance",
        limitations=[
            "Not autonomous remediation — human approval required for apply.",
            "Policy permission does not guarantee operational safety.",
            "Does not claim malware detection or EDR-grade verdicts.",
        ],
    )


def assess_risk(fixture: dict[str, Any]) -> dict[str, Any]:
    tests = run_control_tests(fixture)
    findings = findings_from_fixture(fixture, tests)
    rating = rate_risk(findings, tests, fixture)
    return {
        "schema_version": "technology_risk_decision.v1",
        "command": "risk-assess",
        "case_id": fixture.get("case_id"),
        "business_objective": objective_for_fixture(fixture).model_dump(),
        "asset": asset_for_fixture(fixture).model_dump(),
        "threat": threat_for_fixture(fixture).model_dump(),
        "controls": [c.model_dump() for c in controls_for_fixture(fixture)],
        "findings": [f.model_dump() for f in findings],
        "risk_rating": rating.model_dump(),
        "governance_decision": _governance_decision(fixture).model_dump(),
        "limitations": rating.limitations,
        "disclaimer": (
            "Technology risk assessment for governance support — not antivirus, EDR, or XDR. "
            "Observation ≠ proof; correlation ≠ causation."
        ),
    }


def build_governance_report(fixture: dict[str, Any], *, format: str = "json") -> str | dict[str, Any]:
    assessment = assess_risk(fixture)
    tests = run_control_tests(fixture)
    assessment["control_tests"] = [t.model_dump() for t in tests]

    if format == "json":
        return assessment

    obj = assessment["business_objective"]
    asset = assessment["asset"]
    threat = assessment["threat"]
    rating = assessment["risk_rating"]
    gov = assessment["governance_decision"]
    findings = assessment["findings"]

    lines = [
        "# Technology Risk & Control Governance Report",
        "",
        f"**Case ID:** {fixture.get('case_id', 'N/A')}",
        f"**Schema:** {assessment['schema_version']}",
        "",
        "## Executive Summary",
        "",
        assessment["disclaimer"],
        "",
        rating["summary"],
        "",
        "## Business Objective",
        "",
        f"- **{obj['name']}** — {obj['description']}",
        f"- Owner: {obj['owner']}",
        "",
        "## Asset & Threat",
        "",
        f"- **Asset:** {asset['name']} ({asset['asset_type']})",
        f"- **Threat:** {threat['name']} — {threat['failure_mode']}",
        "",
        "## Findings",
        "",
    ]
    for f in findings:
        lines.append(
            f"- **{f['title']}** ({f['classification']}) — tier: {f['evidence_tier']}, "
            f"confidence: {f['confidence']}"
        )
    lines.extend(
        [
            "",
            "## Risk Rating",
            "",
            f"| Inherent | Residual | Likelihood | Impact | Control effectiveness |",
            f"|----------|----------|------------|--------|----------------------|",
            f"| {rating['inherent_level']} | {rating['residual_level']} | {rating['likelihood']} | "
            f"{rating['impact']} | {rating['control_effectiveness']} |",
            "",
            "## Control Test Results",
            "",
        ]
    )
    for t in tests:
        lines.append(f"- **{t.control_name}**: {t.result.value} — {t.finding_summary}")
    lines.extend(
        [
            "",
            "## Governance Decision",
            "",
            f"- Outcome: **{gov['outcome']}**",
            f"- Dry-run: **{gov['dry_run']}**",
            f"- Recommended action: {gov['recommended_action']}",
            f"- Owner: {gov['governance_owner']}",
            "",
            "## Limitations",
            "",
        ]
    )
    for lim in assessment.get("limitations", []):
        lines.append(f"- {lim}")
    return "\n".join(lines)
