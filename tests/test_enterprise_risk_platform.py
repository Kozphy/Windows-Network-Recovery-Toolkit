"""Enterprise Technology Risk & Control Analytics tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from src.platform_core.business_objectives.catalog import list_objectives
from src.platform_core.control_testing.engine import run_control_tests
from src.platform_core.controls.catalog import get_control
from src.platform_core.enterprise_audit.trail import build_audit_trail, verify_audit_trail
from src.platform_core.risk_platform.pipeline import load_case_fixture, run_risk_analytics_pipeline

REPO = Path(__file__).resolve().parents[1]
CASE1 = REPO / "tests" / "fixtures" / "case_studies" / "case_1_dead_wininet_proxy.json"
CASE2 = REPO / "tests" / "fixtures" / "case_studies" / "case_2_proxy_reverter_node.json"
CASE3 = REPO / "tests" / "fixtures" / "case_studies" / "case_3_tls_mismatch.json"


def test_business_objectives_catalog() -> None:
    objs = list_objectives()
    assert len(objs) >= 5
    assert all(o.regulatory_mapping for o in objs)


def test_control_traces_to_objective() -> None:
    ctrl = get_control("NET-001")
    assert ctrl is not None
    assert ctrl.objective_id == "BO-001"


def test_control_tests_case1_fail_proxy() -> None:
    fixture = load_case_fixture(CASE1)
    tests = run_control_tests(fixture)
    results = {t.control_id: t.result.value for t in tests}
    assert results["NET-001"] == "FAIL"
    assert results["NET-004"] == "PASS"


def test_pipeline_full_traceability_case1() -> None:
    result = run_risk_analytics_pipeline(load_case_fixture(CASE1))
    assert result["business_objectives"]
    assert result["assets"]
    assert result["threats"]
    assert result["controls"]
    assert result["findings"]
    assert result["risk_register"]
    assert result["audit_chain_verified"] is True
    assert "Observation" in result["epistemic_notice"]


def test_pipeline_case3_tls_finding() -> None:
    result = run_risk_analytics_pipeline(load_case_fixture(CASE3))
    assert result["classification"] == "TLS_PATH_MISMATCH"
    assert any(f["control_id"] == "NET-003" for f in result["findings"])


def test_governance_dashboard_metrics() -> None:
    result = run_risk_analytics_pipeline(load_case_fixture(CASE1))
    dash = result["governance_dashboard"]
    assert dash["controls_tested"] >= 3
    assert dash["compliance_percentage"] >= 0


def test_audit_trail_chain() -> None:
    result = run_risk_analytics_pipeline(load_case_fixture(CASE1))
    trail = build_audit_trail(result)
    ok, _ = verify_audit_trail(trail)
    assert ok
    assert trail[0]["previous_hash"] == "genesis"


def test_api_risk_analytics_assess() -> None:
    with TestClient(app) as client:
        resp = client.post(
            "/platform/risk-analytics/assess",
            headers={"X-Operator-Role": "viewer"},
            json={"fixture_path": str(CASE1.relative_to(REPO)).replace("\\", "/"), "dry_run": True},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["audit_chain_verified"] is True


def test_api_governance_dashboard() -> None:
    with TestClient(app) as client:
        resp = client.get(
            "/platform/risk-analytics/governance-dashboard",
            headers={"X-Operator-Role": "viewer"},
            params={"fixture": str(CASE1.relative_to(REPO)).replace("\\", "/")},
        )
    assert resp.status_code == 200
    assert "compliance_percentage" in resp.json()


@pytest.mark.parametrize("case_path", [CASE1, CASE2, CASE3])
def test_pipeline_all_case_studies(case_path: Path) -> None:
    result = run_risk_analytics_pipeline(load_case_fixture(case_path))
    assert result["limitations"]
    assert result["learning_recommendations"]
