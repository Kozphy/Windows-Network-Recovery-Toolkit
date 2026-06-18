"""Control test engine portfolio tests."""

from __future__ import annotations

from pathlib import Path

from src.platform_core.controls.control_test import ControlTestOutcome, run_control_test_suite

AUDIT_FIXTURE = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "risk_analytics" / "audit_sample"


def test_destructive_blocked_passes_safety_control() -> None:
    from src.platform_core.analytics.summary import _load_audit_records

    records, _, _ = _load_audit_records(AUDIT_FIXTURE)
    tests = run_control_test_suite(audit_records=records)
    rem = next(t for t in tests if t.control_id == "CT-REM-003")
    assert rem.result == ControlTestOutcome.PASS


def test_insufficient_evidence_when_no_audit() -> None:
    tests = run_control_test_suite()
    audit = next(t for t in tests if t.control_id == "CT-AUDIT-001")
    assert audit.result == ControlTestOutcome.INSUFFICIENT_EVIDENCE


def test_exception_from_fixture() -> None:
    tests = run_control_test_suite(fixture={"control_test_exception": "Reviewer approved exception"})
    assert any(t.result == ControlTestOutcome.EXCEPTION for t in tests)
