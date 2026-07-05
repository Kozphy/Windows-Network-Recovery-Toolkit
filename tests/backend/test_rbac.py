"""RBAC tests for /v1 API."""

from __future__ import annotations

from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_viewer_cannot_ingest(sample_proxy_evidence):
    headers = {"X-Api-Token": "test-token", "X-Api-Role": "demo_viewer"}
    r = client.post("/v1/evidence", json=sample_proxy_evidence, headers=headers)
    assert r.status_code == 403


def test_operator_can_ingest(sample_proxy_evidence):
    headers = {"X-Api-Token": "test-token", "X-Api-Role": "operator"}
    r = client.post("/v1/evidence", json=sample_proxy_evidence, headers=headers)
    assert r.status_code == 202


def test_auditor_can_read_incidents(sample_proxy_evidence):
    op = {"X-Api-Token": "test-token", "X-Api-Role": "operator"}
    client.post("/v1/evidence", json=sample_proxy_evidence, headers=op)
    aud = {"X-Api-Token": "test-token", "X-Api-Role": "auditor_readonly"}
    r = client.get("/v1/incidents", headers=aud)
    assert r.status_code == 200
