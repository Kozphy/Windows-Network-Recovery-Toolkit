"""Tests for RiskDecisionRecord, proof tiers, mature control tests, and governance upgrades."""

from __future__ import annotations

import json
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from src.platform_core.ai_risk_analyst.guardrails import enforce_advisory_only
from src.platform_core.governance.audit_report import build_audit_governance_report
from src.platform_core.governance.proof_tier import ProofTier, resolve_proof_tier
from src.platform_core.governance.risk_decision_record import (
    RiskDecisionRecord,
    build_risk_decision_record,
)
from src.platform_core.risk.business_impact_mapping import map_business_impact
from src.platform_core.risk.control_test_mature import MatureTestResult, run_mature_control_tests
from src.platform_core.risk.governance_report import assess_risk
from windows_network_toolkit import cli

REPO = Path(__file__).resolve().parents[1]
CASE_1 = REPO / "tests" / "fixtures" / "case_studies" / "case_1_dead_wininet_proxy.json"
DEAD_PROXY = REPO / "examples" / "evidence" / "DEAD_PROXY_CONFIG.json"
MISMATCH = REPO / "examples" / "evidence" / "WININET_WINHTTP_MISMATCH.json"
REVERTER = REPO / "examples" / "evidence" / "REVERTER_SUSPECTED.json"
AUDIT_SAMPLE = REPO / "tests" / "fixtures" / "risk_analytics" / "audit_sample"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_risk_decision_record_json_serializable() -> None:
    fixture = _load(CASE_1)
    record = build_risk_decision_record(fixture, operator_id="analyst-1")
    payload = record.model_dump(mode="json")
    assert payload["schema_version"] == "risk_decision_record.v1"
    assert payload["incident_id"]
    assert payload["classification"] == "DEAD_PROXY_CONFIG"
    assert payload["proof_tier"] in ProofTier.__members__.values()
    assert payload["evidence_hash"]
    assert payload["human_review_required"] is True
    assert "malware" not in " ".join(payload["limitations"]).lower() or "does not" in " ".join(payload["limitations"]).lower()
    roundtrip = RiskDecisionRecord.model_validate(payload)
    assert roundtrip.incident_id == record.incident_id


def test_dead_proxy_proof_tier_capped_without_runtime() -> None:
    fixture = {
        "classification": {"primary_classification": "DEAD_PROXY_CONFIG"},
        "listener_info": {"listener_found": False},
        "proof": {"conclusion": {"status": "not_run"}},
    }
    result = resolve_proof_tier(fixture)
    assert result.proof_tier in (ProofTier.T0_OBSERVATION_ONLY, ProofTier.T1_LOCAL_CONFIG_EVIDENCE)
    assert any("malware" in lim.lower() or "mitm" in lim.lower() for lim in result.limitations)


def test_dead_proxy_with_corroboration_max_t2() -> None:
    fixture = _load(DEAD_PROXY)
    result = resolve_proof_tier(fixture)
    assert result.proof_tier in (
        ProofTier.T1_LOCAL_CONFIG_EVIDENCE,
        ProofTier.T2_RUNTIME_CORROBORATION,
    )
    assert result.proof_tier != ProofTier.T3_BEHAVIORAL_REPRODUCTION


def test_mitm_classification_capped_at_t2() -> None:
    fixture = _load(REPO / "examples" / "evidence" / "POSSIBLE_MITM_RISK.json")
    result = resolve_proof_tier(fixture)
    assert result.proof_tier in (
        ProofTier.T0_OBSERVATION_ONLY,
        ProofTier.T1_LOCAL_CONFIG_EVIDENCE,
        ProofTier.T2_RUNTIME_CORROBORATION,
    )


def test_business_impact_mapping_dead_proxy() -> None:
    mapping = map_business_impact("DEAD_PROXY_CONFIG")
    assert "connectivity" in mapping.user_impact.lower()
    assert "IT support" in mapping.suggested_forum or "Technology risk" in mapping.suggested_forum


def test_mature_control_tests_cover_six_scenarios() -> None:
    fixture = _load(CASE_1)
    tests = run_mature_control_tests(fixture)
    assert len(tests) == 6
    ids = {t.control_id for t in tests}
    assert "CTRL-EPR-001" in ids
    assert "CTRL-EPR-006" in ids
    dead = next(t for t in tests if t.control_id == "CTRL-EPR-001")
    assert dead.test_result in (MatureTestResult.PASS, MatureTestResult.PARTIAL)


def test_mature_control_mismatch_fixture() -> None:
    tests = run_mature_control_tests(_load(MISMATCH))
    mismatch = next(t for t in tests if t.control_id == "CTRL-EPR-002")
    assert mismatch.test_result == MatureTestResult.PASS
    assert mismatch.remediation_owner


def test_mature_control_reverter_partial_without_watch() -> None:
    tests = run_mature_control_tests(_load(REVERTER))
    rev = next(t for t in tests if t.control_id == "CTRL-EPR-006")
    assert rev.test_result in (MatureTestResult.PASS, MatureTestResult.PARTIAL)


def test_assess_risk_includes_decision_record() -> None:
    payload = assess_risk(_load(CASE_1))
    assert "risk_decision_record" in payload
    assert payload["risk_decision_record"]["execution_authority"] == "preview_only"
    assert "mature_control_tests" in payload
    assert len(payload["mature_control_tests"]) == 6


def test_audit_governance_report_v2_sections() -> None:
    report = build_audit_governance_report(AUDIT_SAMPLE, format="json")
    assert isinstance(report, dict)
    assert report["schema_version"] == "audit_governance_report.v2"
    assert "incident_volume_by_classification" in report
    assert "top_recurring_risk_themes" in report
    assert "control_test_summary" in report
    assert "human_review_queue" in report
    assert "ai_usage_transparency" in report
    assert "appendix" in report
    assert report["limitations"]


def test_governance_report_markdown_executive_sections() -> None:
    cap = StringIO()
    with patch("sys.stdout", cap):
        rc = cli.main(
            ["governance-report", "--audit-dir", str(AUDIT_SAMPLE), "--format", "markdown"],
            prog="test",
        )
    assert rc == 0
    text = cap.getvalue()
    assert "Executive Summary" in text
    assert "Human-review queue" in text
    assert "AI usage transparency" in text
    assert "Audit integrity" in text


def test_ai_cannot_elevate_execution_authority() -> None:
    advisory = {
        "recommended_action": "DISABLE_WININET_PROXY",
        "execution_authority": "automated_execute",
        "narrative": "Safe to execute automatically without review.",
    }
    sanitized = enforce_advisory_only(advisory)
    assert sanitized["execution_authority"] != "automated_execute"
    assert "automated" not in sanitized.get("narrative", "").lower() or "preview" in sanitized.get("narrative", "").lower()
