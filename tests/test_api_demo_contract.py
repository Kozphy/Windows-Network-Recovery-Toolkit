"""API demo contract tests — complements tests/api/test_technology_risk_routes.py."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_root_health_standard_mode() -> None:
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["mode"] in ("standard", "demo")


def test_root_health_demo_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEMO_MODE", "true")
    r = client.get("/health")
    body = r.json()
    assert body["status"] == "ok"
    assert body["mode"] == "demo"


def test_trisk_health_non_claim_positioning() -> None:
    r = client.get("/trisk/health")
    body = r.json()
    assert body["status"] == "ok"
    positioning = body.get("positioning", "").lower()
    assert "not antivirus" in positioning or "management information" in positioning


def test_incidents_include_limitations_when_present() -> None:
    r = client.get("/incidents")
    body = r.json()
    assert r.status_code == 200
    for item in body.get("items", []):
        if "limitations" in item:
            assert isinstance(item["limitations"], list)


def test_executive_report_management_information_boundary() -> None:
    r = client.get("/reports/executive")
    body = r.json()
    assert r.status_code == 200
    blob = json_dumps_lower(body)
    assert "management information" in blob or "governance" in blob


def json_dumps_lower(obj: object) -> str:
    import json

    return json.dumps(obj).lower()
