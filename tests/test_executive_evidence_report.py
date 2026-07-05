"""Tests for executive evidence report (Phase 4)."""

from __future__ import annotations

import json
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from src.platform_core.analytics.executive_evidence_report import (
    build_executive_evidence_report,
    format_executive_evidence_markdown,
)
from windows_network_toolkit import cli

REPO = Path(__file__).resolve().parents[1]
AUDIT_SAMPLE = REPO / "tests" / "fixtures" / "risk_analytics" / "audit_sample"
REGISTER = REPO / "tests" / "fixtures" / "risk_register" / "sample_risk_register.json"
CLOUD_FIXTURE = REPO / "tests" / "fixtures" / "cloud_governance" / "mock_recommendations.json"
FINOPS_FIXTURE = REPO / "tests" / "fixtures" / "finops" / "mock_costs.json"


def test_executive_evidence_report_structure() -> None:
    report = build_executive_evidence_report(
        risk_register_path=REGISTER,
        cloud_fixture_path=CLOUD_FIXTURE,
        finops_fixture_path=FINOPS_FIXTURE,
        audit_dir=AUDIT_SAMPLE,
    )
    assert report["schema_version"] == "executive_evidence_report.v1"
    assert report["executive_summary"]["total_risks"] == 3
    assert report["top_risks"]
    assert report["top_cost_saving_opportunities"]
    assert report["recommended_next_actions"]
    assert report["governance"]["classification_is_accusation"] is False


def test_executive_evidence_markdown_sections() -> None:
    report = build_executive_evidence_report(
        risk_register_path=REGISTER,
        cloud_fixture_path=CLOUD_FIXTURE,
        finops_fixture_path=FINOPS_FIXTURE,
    )
    md = format_executive_evidence_markdown(report)
    for section in (
        "## Executive summary",
        "## Top risks",
        "## Top cost-saving opportunities",
        "## Control gaps",
        "## Evidence limitations",
        "## Recommended next actions",
    ):
        assert section in md


def test_cli_evidence_report_executive_smoke() -> None:
    cap = StringIO()
    with patch("sys.stdout", cap):
        rc = cli.main(
            [
                "evidence-report",
                "--executive",
                "--risk-register",
                str(REGISTER),
                "--cloud-fixture",
                str(CLOUD_FIXTURE),
                "--finops-fixture",
                str(FINOPS_FIXTURE),
                "--audit-dir",
                str(AUDIT_SAMPLE),
                "--format",
                "markdown",
            ],
            prog="test",
        )
    assert rc == 0
    text = cap.getvalue()
    assert "Executive Evidence Report" in text
