"""Governance decision and management reporting."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from src.platform_core.governance.evidence_to_action import attach_governance_envelope
from src.platform_core.governance.proof_tier import resolve_proof_tier
from src.platform_core.governance.report_sections import AI_TRANSPARENCY_SECTION, NON_CLAIMS
from src.platform_core.governance.risk_decision_record import build_risk_decision_record
from src.platform_core.risk.business_impact_mapping import map_business_impact
from src.platform_core.risk.control_test_mature import run_mature_control_tests

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
    mature_tests = run_mature_control_tests(fixture)
    findings = findings_from_fixture(fixture, tests)
    rating = rate_risk(findings, tests, fixture)
    decision_record = build_risk_decision_record(fixture)
    proof_tier_result = resolve_proof_tier(fixture)
    impact_map = map_business_impact(
        str((fixture.get("classification") or {}).get("primary_classification") or "")
    )
    result = {
        "schema_version": "technology_risk_decision.v1",
        "command": "risk-assess",
        "case_id": fixture.get("case_id"),
        "risk_decision_record": decision_record.model_dump(mode="json"),
        "proof_tier": proof_tier_result.model_dump(),
        "business_impact_forum": impact_map.model_dump(),
        "mature_control_tests": [t.model_dump() for t in mature_tests],
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
    classification = (fixture.get("classification") or {}).get("primary_classification")
    policy = fixture.get("policy_decision") or {}
    proof_block = fixture.get("proof") or {}
    conclusion = proof_block.get("conclusion") if isinstance(proof_block, dict) else {}
    evidence_tier = proof_tier_result.proof_tier.value
    return attach_governance_envelope(
        result,
        primary_classification=classification,
        evidence_tier=evidence_tier,
        proof_conclusion=conclusion.get("status") if isinstance(conclusion, dict) else None,
        policy_outcome=policy.get("outcome"),
        dry_run=bool(fixture.get("dry_run", True) or policy.get("dry_run", True)),
        requires_confirmation=bool(policy.get("requires_confirmation", True)),
    )


def build_governance_report(fixture: dict[str, Any], *, format: str = "json") -> str | dict[str, Any]:
    assessment = assess_risk(fixture)
    tests = run_control_tests(fixture)
    mature = run_mature_control_tests(fixture)
    assessment["control_tests"] = [t.model_dump() for t in tests]
    assessment["mature_control_tests"] = [t.model_dump() for t in mature]

    if format == "json":
        return assessment

    obj = assessment["business_objective"]
    asset = assessment["asset"]
    threat = assessment["threat"]
    rating = assessment["risk_rating"]
    gov = assessment["governance_decision"]
    findings = assessment["findings"]
    rdr = assessment.get("risk_decision_record") or {}
    proof = assessment.get("proof_tier") or {}

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
        f"**Proof tier:** {rdr.get('proof_tier', proof.get('proof_tier', 'n/a'))} — "
        f"**Risk rating:** {rdr.get('risk_rating', rating.get('residual_level'))}",
        "",
        rating["summary"],
        "",
        "## Risk Decision Record",
        "",
        f"- Incident: {rdr.get('incident_id')}",
        f"- Classification: {rdr.get('classification')}",
        f"- Human review required: {rdr.get('human_review_required')}",
        f"- Execution authority: {rdr.get('execution_authority')}",
        f"- Evidence hash: `{rdr.get('evidence_hash', '')[:16]}...`",
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
            "| Inherent | Residual | Likelihood | Impact | Control effectiveness |",
            "|----------|----------|------------|--------|----------------------|",
            f"| {rating['inherent_level']} | {rating['residual_level']} | {rating['likelihood']} | "
            f"{rating['impact']} | {rating['control_effectiveness']} |",
            "",
            "## Control Test Results",
            "",
        ]
    )
    for t in tests:
        lines.append(f"- **{t.control_name}**: {t.result.value} — {t.finding_summary}")
    lines.extend(["", "## Mature control tests", ""])
    for mt in mature:
        lines.append(f"- **{mt.control_name}** ({mt.test_result.value}): {mt.control_objective}")
    lines.extend(
        [
            "",
            "## AI usage transparency",
            "",
            AI_TRANSPARENCY_SECTION["human_review_required"],
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
    lines.extend(["", "## Non-claims", ""])
    for lim in NON_CLAIMS:
        lines.append(f"- {lim}")
    return "\n".join(lines)
