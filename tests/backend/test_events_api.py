"""Tests for /v1 events and health endpoints."""

from __future__ import annotations

from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_v1_health():
    r = client.get("/v1/health")
    assert r.status_code == 200
    assert "status" in r.json()


def test_v1_events_requires_auth():
    r = client.get("/v1/events")
    assert r.status_code == 401


def test_v1_events_list(auth_headers, sample_proxy_evidence):
    client.post("/v1/evidence", json=sample_proxy_evidence, headers=auth_headers)
    headers = {**auth_headers, "X-Api-Role": "auditor_readonly"}
    r = client.get("/v1/events", headers=headers)
    assert r.status_code == 200
    assert "items" in r.json()
