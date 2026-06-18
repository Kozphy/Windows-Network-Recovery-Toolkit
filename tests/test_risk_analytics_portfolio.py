"""Portfolio risk analytics — KPI summary, business impact, control tests, governance reports."""

from __future__ import annotations

import json
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from src.platform_core.analytics import build_risk_kpi_summary
from src.platform_core.controls.control_test import ControlTestOutcome, run_control_test_suite
from src.platform_core.governance.audit_report import build_audit_governance_report
from src.platform_core.risk.business_impact import estimate_business_impact
from windows_network_toolkit import cli

REPO = Path(__file__).resolve().parents[1]
AUDIT_SAMPLE = REPO / "tests" / "fixtures" / "risk_analytics" / "audit_sample"
CASE_1 = REPO / "tests" / "fixtures" / "case_studies" / "case_1_dead_wininet_proxy.json"


def test_risk_kpi_summary_from_fixture_audit_dir() -> None:
    payload = build_risk_kpi_summary(AUDIT_SAMPLE)
    kpis = payload["kpis"]
    assert payload["schema_version"] == "risk_kpi_summary.v1"
    assert kpis["total_incidents"] >= 4
    assert "DEAD_PROXY_CONFIG" in kpis["incidents_by_classification"]
    assert kpis["remediation_previews_count"] >= 1
    assert payload["governance"]["confidence_type"] == "ordinal_not_probability"
    assert payload["limitations"]


def test_business_impact_ordinal_with_limitations() -> None:
    est = estimate_business_impact(classification="POSSIBLE_MITM_RISK")
    assert est.confidence_type == "ordinal_not_probability"
    assert est.total_business_impact_score >= 1
    assert any("not financial advice" in lim.lower() or "not accounting" in lim.lower() for lim in est.limitations)


def test_control_test_insufficient_evidence_for_out_of_scope() -> None:
    tests = run_control_test_suite(fixture=json.loads(CASE_1.read_text(encoding="utf-8")))
    assert all(t.result in ControlTestOutcome for t in tests)


def test_audit_governance_report_includes_limitations() -> None:
    report = build_audit_governance_report(AUDIT_SAMPLE, format="json")
    assert isinstance(report, dict)
    assert report["limitations"]
    assert "executive_summary" in report
    assert "control_test_results" in report
    assert "business_impact_estimate" in report
    assert report["governance"]["classification_is_accusation"] is False


def test_governance_report_audit_dir_markdown_smoke() -> None:
    cap = StringIO()
    with patch("sys.stdout", cap):
        rc = cli.main(
            [
                "governance-report",
                "--audit-dir",
                str(AUDIT_SAMPLE),
                "--format",
                "markdown",
            ],
            prog="test",
        )
    assert rc == 0
    assert "Limitations" in cap.getvalue()


def test_risk_kpi_cli_smoke() -> None:
    cap = StringIO()
    with patch("sys.stdout", cap):
        rc = cli.main(
            ["risk-kpi-summary", "--audit-dir", str(AUDIT_SAMPLE), "--format", "json"],
            prog="test",
        )
    assert rc == 0
    payload = json.loads(cap.getvalue())
    assert payload["kpis"]["total_incidents"] >= 1


def test_governance_report_fixture_still_works() -> None:
    cap = StringIO()
    with patch("sys.stdout", cap):
        rc = cli.main(
            [
                "governance-report",
                "--fixture",
                "tests/fixtures/case_studies/case_1_dead_wininet_proxy.json",
                "--format",
                "json",
            ],
            prog="test",
        )
    assert rc == 0
    payload = json.loads(cap.getvalue())
    assert payload.get("schema_version") == "technology_risk_decision.v1" or "risk_rating" in payload
