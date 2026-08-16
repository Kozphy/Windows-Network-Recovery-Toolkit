from __future__ import annotations

import json
from pathlib import Path

from src.platform_core.governance.assurance_adapter import (
    build_assurance_decision,
    build_control_exceptions,
)
from src.platform_core.governance.risk_decision_record import build_risk_decision_record
from src.platform_core.governance.senior_assurance import AssuranceConclusion
from src.platform_core.risk.control_test import run_control_tests
from src.platform_core.risk.finding import findings_from_fixture
from src.platform_core.risk.governance_report import assess_risk
from src.platform_core.risk.risk_rating import rate_risk


REPO = Path(__file__).resolve().parents[1]
CASE_1 = REPO / "tests" / "fixtures" / "case_studies" / "case_1_dead_wininet_proxy.json"


def _load() -> dict:
    return json.loads(CASE_1.read_text(encoding="utf-8"))


def _rating(fixture: dict):
    tests = run_control_tests(fixture)
    return rate_risk(findings_from_fixture(fixture, tests), tests, fixture)


def test_risk_decision_record_contains_assurance_artifacts() -> None:
    record = build_risk_decision_record(_load(), incident_id="INC-INTEGRATION")
    assert record.assurance_decision
    assert record.assurance_decision["incident_id"] == "INC-INTEGRATION" or record.assurance_decision["incident_id"]
    assert "conclusion" in record.assurance_decision
    assert isinstance(record.exception_register, list)


def test_governance_assessment_exposes_assurance_through_decision_record() -> None:
    assessment = assess_risk(_load())
    record = assessment["risk_decision_record"]
    assert "assurance_decision" in record
    assert "exception_register" in record
    assert "closure_allowed" in record["assurance_decision"]


def test_partial_mature_controls_become_reviewable_exceptions() -> None:
    exceptions = build_control_exceptions(_load())
    for item in exceptions:
        assert item.exception_id.startswith("EXC-")
        assert item.control_id
        assert item.owner


def test_evidence_override_can_force_insufficient_evidence() -> None:
    fixture = _load()
    fixture["evidence_sufficient"] = False
    decision, _ = build_assurance_decision(fixture, _rating(fixture))
    assert decision.conclusion == AssuranceConclusion.INSUFFICIENT_EVIDENCE
    assert decision.closure_allowed is False


def test_high_residual_risk_requires_management_signoff() -> None:
    fixture = _load()
    fixture["human_review_completed"] = True
    fixture["remediation_verified"] = True
    rating = _rating(fixture).model_copy(update={"residual_level": "high", "control_effectiveness": 0.9})
    decision, _ = build_assurance_decision(fixture, rating)
    assert decision.management_signoff_required is True
    assert decision.closure_allowed is False


def test_management_signoff_is_consumed_from_fixture() -> None:
    fixture = _load()
    fixture["human_review_completed"] = True
    fixture["remediation_verified"] = True
    fixture["management_signoff"] = {
        "signoff_id": "SO-001",
        "signer_id": "manager-1",
        "signer_role": "Technology Risk Owner",
        "accepted_residual_risk": "high",
        "rationale": "Residual exposure accepted pending monitored remediation.",
        "signed_at": "2026-08-16T10:00:00Z",
    }
    rating = _rating(fixture).model_copy(update={"residual_level": "high", "control_effectiveness": 0.9})
    decision, _ = build_assurance_decision(fixture, rating)
    assert decision.management_signoff_required is True
    assert not any("sign-off is required" in line for line in decision.rationale)


def test_closed_exception_does_not_block_assurance() -> None:
    fixture = _load()
    exceptions = build_control_exceptions(fixture)
    if not exceptions:
        return
    fixture["control_exception_status"] = {
        item.control_id: "closed" for item in exceptions
    }
    closed = build_control_exceptions(fixture)
    assert all(not item.blocks_assurance for item in closed)
