"""Technology Risk Analytics API route tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


@pytest.mark.parametrize(
    "path",
    [
        "/trisk/health",
        "/incidents",
        "/risks",
        "/controls",
        "/reports/executive",
    ],
)
def test_technology_risk_routes_not_404(path: str) -> None:
    r = client.get(path)
    assert r.status_code == 200


def test_trisk_health_payload() -> None:
    r = client.get("/trisk/health")
    body = r.json()
    assert body["status"] == "ok"
    assert body["api"] == "technology-risk-analytics"
    assert "not antivirus" in body["positioning"].lower()


def test_incidents_list_shape() -> None:
    r = client.get("/incidents")
    body = r.json()
    assert "items" in body
    assert "total" in body
    assert body["schema_version"] == "endpoint_evidence_analytics.v1"


def test_risks_list_has_scores() -> None:
    r = client.get("/risks")
    body = r.json()
    assert body["schema_version"] == "technology_risk_scoring.v1"
    if body["total"] > 0:
        item = body["items"][0]
        assert "risk_score" in item
        assert "risk_level" in item
        assert "explanation" in item


def test_controls_catalog() -> None:
    r = client.get("/controls")
    body = r.json()
    assert "control_tests" in body
    assert "incident_control_map" in body
    assert any(m["incident_class"] == "DEAD_PROXY_CONFIG" for m in body["incident_control_map"])


def test_executive_report_schema() -> None:
    r = client.get("/reports/executive")
    body = r.json()
    assert body["schema_version"] == "technology_risk_executive_report.v1"
    assert "executive_summary" in body
    assert "governance_principles" in body
    assert "not antivirus" in body["positioning"].lower()
