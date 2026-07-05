"""Evidence ingestion tests."""

from __future__ import annotations

from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_get_evidence_after_ingest(sample_proxy_evidence, auth_headers):
    ing = client.post("/v1/evidence", json=sample_proxy_evidence, headers=auth_headers)
    assert ing.status_code == 202
    event_id = ing.json()["event_id"]
    r = client.get(f"/v1/evidence/{event_id}", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["event_id"] == event_id


def test_list_incidents_after_classify(sample_proxy_evidence, auth_headers):
    client.post("/v1/evidence", json=sample_proxy_evidence, headers=auth_headers)
    r = client.get("/v1/incidents", headers=auth_headers)
    assert r.status_code == 200
    assert "items" in r.json()
