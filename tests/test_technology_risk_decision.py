"""Tests for Technology Risk Decision Platform CLI and models."""

from __future__ import annotations

import json
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest

from src.platform_core.risk import (
    assess_risk,
    build_governance_report,
    load_fixture,
    run_control_tests,
)
from windows_network_toolkit import cli

REPO = Path(__file__).resolve().parents[1]
CASE_1 = REPO / "tests" / "fixtures" / "case_studies" / "case_1_dead_wininet_proxy.json"


def _run(args: list[str]) -> tuple[int, str]:
    cap = StringIO()
    with patch("sys.stdout", cap):
        rc = cli.main(args)
    return rc, cap.getvalue()


@pytest.fixture
def case_fixture() -> dict:
    return load_fixture(CASE_1)


def test_case_fixture_loads(case_fixture: dict) -> None:
    assert case_fixture["case_id"] == "CASE_1_DEAD_WININET_PROXY"
    assert case_fixture["classification"]["primary_classification"] == "DEAD_PROXY_CONFIG"


def test_control_tests_detect_drift(case_fixture: dict) -> None:
    tests = run_control_tests(case_fixture)
    drift = next(t for t in tests if t.test_id == "CT_PROXY_DRIFT")
    assert drift.result.value == "FAIL"
    safety = next(t for t in tests if t.test_id == "CT_REMEDIATION_SAFETY")
    assert safety.result.value == "PASS"


def test_risk_assess_includes_governance(case_fixture: dict) -> None:
    result = assess_risk(case_fixture)
    assert result["risk_rating"]["inherent_level"] == "medium"
    assert result["governance_decision"]["dry_run"] is True
    assert result["governance_decision"]["outcome"] == "PREVIEW_ONLY"
    assert "malware" in result["disclaimer"].lower() or "edr" in result["disclaimer"].lower()


def test_governance_report_markdown(case_fixture: dict) -> None:
    md = build_governance_report(case_fixture, format="markdown")
    assert isinstance(md, str)
    assert "Technology Risk & Control Governance Report" in md
    assert "DEAD_PROXY_CONFIG" in md


def test_cli_risk_assess() -> None:
    rc, out = _run([
        "risk-assess",
        "--fixture",
        "tests/fixtures/case_studies/case_1_dead_wininet_proxy.json",
    ])
    assert rc == 0
    payload = json.loads(out)
    assert payload["command"] == "risk-assess"
    assert payload["findings"]


def test_cli_control_test() -> None:
    rc, out = _run([
        "control-test",
        "--fixture",
        "case_1_dead_wininet_proxy.json",
    ])
    assert rc == 0
    payload = json.loads(out)
    assert payload["command"] == "control-test"
    assert len(payload["control_tests"]) >= 4


def test_cli_governance_report_markdown() -> None:
    rc, out = _run([
        "governance-report",
        "--fixture",
        "case_1_dead_wininet_proxy.json",
        "--format",
        "markdown",
    ])
    assert rc == 0
    assert "Governance Decision" in out
