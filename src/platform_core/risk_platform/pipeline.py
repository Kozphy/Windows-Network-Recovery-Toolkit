"""Technology Risk & Control Analytics — end-to-end pipeline."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from platform_core.models import utc_now_iso
from src.platform_core.assets.catalog import assets_for_fixture
from src.platform_core.business_objectives.catalog import list_objectives
from src.platform_core.control_testing.engine import run_control_tests
from src.platform_core.controls.catalog import controls_for_classification
from src.platform_core.enterprise.enums import EPISTEMIC_NOTICE
from src.platform_core.enterprise_audit.trail import build_audit_trail, verify_audit_trail
from src.platform_core.enterprise_learning.recommender import generate_learning_recommendations
from src.platform_core.findings.generator import generate_findings
from src.platform_core.governance_metrics.dashboard import build_governance_dashboard
from src.platform_core.remediation_lifecycle.planner import create_remediations
from src.platform_core.risk_assessment.engine import assess_risks
from src.platform_core.threats.catalog import threats_for_classification

_REPO = Path(__file__).resolve().parents[3]


def load_case_fixture(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    if not p.is_file():
        p = _REPO / path
    return json.loads(p.read_text(encoding="utf-8"))


def run_risk_analytics_pipeline(fixture: dict[str, Any]) -> dict[str, Any]:
    """Transform technical observations into business-aligned risk intelligence."""
    classification = (fixture.get("classification") or {}).get("primary_classification", "NO_PROXY")
    objectives = [o for o in list_objectives() if o.id in ("BO-001", "BO-003", "BO-004", "BO-005")]
    assets = assets_for_fixture(classification)
    threats = threats_for_classification(classification)
    controls = controls_for_classification(classification)
    tests = run_control_tests(fixture)
    asset_ids = [a.asset_id for a in assets]
    findings = generate_findings(tests, fixture, asset_ids=asset_ids)
    risk_assessments, risk_register = assess_risks(findings, threats, tests)
    remediations = create_remediations(findings, fixture)
    dashboard = build_governance_dashboard(tests, findings, remediations)
    learning = generate_learning_recommendations(tests, fixture)

    policy = fixture.get("policy_decision") or {}
    result = {
        "assessment_id": f"TRA-{uuid.uuid4().hex[:12]}",
        "timestamp_utc": utc_now_iso(),
        "case_id": fixture.get("case_id"),
        "classification": classification,
        "evidence_tier": (fixture.get("classification") or {}).get("evidence_tier", "OBSERVED_ONLY"),
        "policy_decision": policy.get("outcome"),
        "epistemic_notice": EPISTEMIC_NOTICE,
        "business_objectives": [o.model_dump() for o in objectives],
        "assets": [a.model_dump() for a in assets],
        "threats": [t.model_dump() for t in threats],
        "controls": [c.model_dump() for c in controls],
        "control_tests": [t.model_dump() for t in tests],
        "findings": [f.model_dump() for f in findings],
        "risk_assessments": [r.model_dump() for r in risk_assessments],
        "risk_register": [r.model_dump() for r in risk_register],
        "remediations": [r.model_dump() for r in remediations],
        "governance_dashboard": dashboard.model_dump(),
        "learning_recommendations": [lr.model_dump() for lr in learning],
        "limitations": list((fixture.get("classification") or {}).get("limitations") or []) + [
            EPISTEMIC_NOTICE,
        ],
    }
    trail = build_audit_trail(result)
    ok, msg = verify_audit_trail(trail)
    result["audit_trail"] = trail
    result["audit_chain_verified"] = ok
    result["audit_chain_message"] = msg
    return result


def executive_summary_markdown(result: dict[str, Any]) -> str:
    dash = result.get("governance_dashboard") or {}
    lines = [
        "# Technology Risk & Control Analytics — Executive Summary",
        "",
        f"**Assessment:** {result.get('assessment_id')}",
        f"**Classification:** {result.get('classification')}",
        f"**Generated:** {result.get('timestamp_utc')}",
        "",
        "## Governance metrics",
        f"- Controls tested: {dash.get('controls_tested')}",
        f"- Controls failed: {dash.get('controls_failed')}",
        f"- Compliance %: {dash.get('compliance_percentage')}",
        f"- High-risk findings: {dash.get('high_risk_findings')}",
        f"- Open remediations: {dash.get('open_remediations')}",
        "",
        "## Traceability",
        "Business Objective → Asset → Threat → Control → Test → Finding → Risk → Remediation → Audit → Learning",
        "",
        "## Limitations",
    ]
    for lim in result.get("limitations") or []:
        lines.append(f"- {lim}")
    lines.append("")
    lines.append("_Not EDR, antivirus, or autonomous remediation._")
    return "\n".join(lines) + "\n"
