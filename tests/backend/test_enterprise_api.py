"""Enterprise decision platform API tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.db import init_trisk_schema, reset_engine
from backend.main import app
from src.platform_core.events import reset_event_store

HEADERS = {
    "X-Api-Token": "test-token",
    "X-Api-Role": "operator",
    "X-Api-Tenant": "default",
}

client = TestClient(app)


@pytest.fixture(autouse=True)
def _db(tmp_path, monkeypatch):
    db_path = tmp_path / "enterprise_test.db"
    monkeypatch.setenv("TRISK_DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("TRISK_API_TOKEN", "test-token")
    reset_engine()
    reset_event_store()
    init_trisk_schema()
    yield


def test_enterprise_health():
    r = client.get("/v1/enterprise/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_policy_evaluate_suspicious_proxy():
    r = client.post(
        "/v1/enterprise/policy/evaluate",
        headers=HEADERS,
        json={
            "classification": "SUSPICIOUS_PROXY",
            "confidence_score": 0.8,
            "requested_action": "observe",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["requires_human_approval"] is True
    assert "limitations" in body


def test_pipeline_run_dead_proxy():
    r = client.post(
        "/v1/enterprise/pipeline/run",
        headers=HEADERS,
        json={
            "endpoint_id": "ep-test-1",
            "signal_type": "proxy_state",
            "raw_observation": {
                "wininet_proxy_enabled": True,
                "wininet_proxy_server": "127.0.0.1:59081",
                "winhttp_direct_access": True,
                "localhost_port": 59081,
            },
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["correlation_id"]
    assert body["decision_id"]
    assert body["evidence_event_id"]
    assert "limitations" in body


def test_audit_logs_after_pipeline():
    client.post(
        "/v1/enterprise/pipeline/run",
        headers=HEADERS,
        json={
            "endpoint_id": "ep-audit-1",
            "raw_observation": {"wininet_proxy_enabled": True},
        },
    )
    r = client.get("/v1/enterprise/audit/logs", headers={**HEADERS, "X-Api-Role": "auditor_readonly"})
    assert r.status_code == 200
    assert r.json()["total"] >= 1


def test_audit_verify_chain():
    client.post(
        "/v1/enterprise/pipeline/run",
        headers=HEADERS,
        json={"endpoint_id": "ep-verify", "raw_observation": {"wininet_proxy_enabled": False}},
    )
    r = client.get(
        "/v1/enterprise/audit/verify",
        headers={**HEADERS, "X-Api-Role": "auditor_readonly"},
    )
    assert r.status_code == 200
    assert r.json()["verified"] is True
