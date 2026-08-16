from __future__ import annotations

import json
from pathlib import Path

from src.platform_core.governance.assurance_integration import (
    assess_fixture_assurance,
    assurance_register,
    build_assurance_input,
)
from src.platform_core.governance.risk_decision_record import build_risk_decision_record
from src.platform_core.governance.senior_assurance import AssuranceConclusion
from src.platform_core.risk.control_test import run_control_tests
from src.platform_core.risk.control_test_mature import run_mature_control_tests
from src.platform_core.risk.finding import findings_from_fixture
from src.platform_core.risk.governance_report import assess_risk
from src.platform_core.risk.risk_rating import rate_risk


REPO = Path(__file__).resolve().parents[1]
CASE_1 = REPO / "tests" / "fixtures" / "case_studies" / "case_1_dead_wininet_proxy.json"


def _load() -> dict:
    return json.loads(CASE_1.read_text(encoding="utf-8"))


def _assessment_parts(fixture: dict):
    tests = run_control_tests(fixture)
    mature = run_mature_control_tests(fixture)
    rating = rate_risk(findings_from_fixture(fixture, tests), tests, fixture)
    return tests, mature, rating


def test_risk_decision_record_contains_assurance_artifacts() -> None:
    record = build_risk_decision_record(_load(), incident_id="INC-INTEGRATION")
    assert record.assurance_decision
    assert record.assurance_decision["incident_id"] == "INC-INTEGRATION"
    assert "conclusion" in record.assurance_decision
    assert isinstance(record.exception_register, list)


def test_governance_assessment_exposes_assurance_through_decision_record() -> None:
    assessment = assess_risk(_load())
    record = assessment["risk_decision_record"]
    assert "assurance_decision" in record
    assert "exception_register" in record
    assert "closure_allowed" in record["assurance_decision"]


def test_partial_mature_controls_become_reviewable_exceptions() -> None:
    fixture = _load()
    register = assurance_register(fixture, mature_tests=run_mature_control_tests(fixture))
    for item in register:
        assert item["exception_id"].startswith("EXC-")
        assert item["control_id"]
        assert item["owner"]


def test_evidence_override_can_force_insufficient_evidence() -> None:
    fixture = _load()
    fixture["assurance"] = {"evidence_sufficient": False}
    tests, mature, rating = _assessment_parts(fixture)
    decision = assess_fixture_assurance(
        fixture,
        rating=rating,
        control_tests=tests,
        mature_tests=mature,
        incident_id="INC-EVIDENCE",
    )
    assert decision.conclusion == AssuranceConclusion.INSUFFICIENT_EVIDENCE
    assert decision.closure_allowed is False


def test_high_residual_risk_requires_management_signoff() -> None:
    fixture = _load()
    fixture["assurance"] = {
        "human_review_completed": True,
        "remediation_verified": True,
    }
    tests, mature, rating = _assessment_parts(fixture)
    rating = rating.model_copy(update={"residual_level": "high", "control_effectiveness": 0.9})
    normalized = build_assurance_input(
        fixture,
        rating=rating,
        control_tests=tests,
        mature_tests=mature,
        incident_id="INC-HIGH-RISK",
    )
    assert normalized.residual_risk.value == "high"
    decision = assess_fixture_assurance(
        fixture,
        rating=rating,
        control_tests=tests,
        mature_tests=mature,
        incident_id="INC-HIGH-RISK",
    )
    assert decision.management_signoff_required is True
    assert decision.closure_allowed is False


def test_closed_exception_without_validation_is_reopened_for_validation() -> None:
    fixture = _load()
    mature = run_mature_control_tests(fixture)
    candidates = [t for t in mature if t.test_result.value in {"FAIL", "PARTIAL"}]
    if not candidates:
        return
    control_id = candidates[0].control_id
    fixture["assurance"] = {
        "exceptions": [
            {
                "control_id": control_id,
                "status": "closed",
                "validation_evidence_ids": [],
            }
        ]
    }
    register = assurance_register(fixture, mature_tests=mature)
    item = next(entry for entry in register if entry["control_id"] == control_id)
    assert item["status"] == "pending_validation"


def test_validated_closed_exception_can_be_closed() -> None:
    fixture = _load()
    mature = run_mature_control_tests(fixture)
    candidates = [t for t in mature if t.test_result.value in {"FAIL", "PARTIAL"}]
    if not candidates:
        return
    control_id = candidates[0].control_id
    fixture["assurance"] = {
        "exceptions": [
            {
                "control_id": control_id,
                "status": "closed",
                "validation_evidence_ids": ["EV-VERIFY-001"],
            }
        ]
    }
    register = assurance_register(fixture, mature_tests=mature)
    item = next(entry for entry in register if entry["control_id"] == control_id)
    assert item["status"] == "closed"
    assert item["validation_evidence_ids"] == ["EV-VERIFY-001"]
