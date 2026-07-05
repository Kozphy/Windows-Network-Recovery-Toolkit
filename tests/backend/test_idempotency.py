"""Idempotent evidence ingestion."""

from __future__ import annotations

from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_duplicate_evidence_same_hash(sample_proxy_evidence, auth_headers):
    r1 = client.post("/v1/evidence", json=sample_proxy_evidence, headers=auth_headers)
    r2 = client.post("/v1/evidence", json=sample_proxy_evidence, headers=auth_headers)
    assert r1.status_code == 202
    assert r2.status_code == 202
    assert r1.json()["event_id"] == r2.json()["event_id"]
    assert r2.json()["created"] is False
