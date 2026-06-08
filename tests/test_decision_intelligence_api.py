from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.decision_intelligence.store import JsonlDecisionIntelligenceStore, reset_store
from backend.main import app


@pytest.fixture
def di_client(tmp_path, monkeypatch):
    monkeypatch.setenv("PLATFORM_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("DATABASE_URL", "")
    reset_store()
    store = JsonlDecisionIntelligenceStore(tmp_path / "decision_intelligence")
    for target in (
        "backend.decision_intelligence.store.get_store",
        "backend.decision_intelligence.service.get_store",
        "backend.decision_intelligence.routes.get_store",
    ):
        monkeypatch.setattr(target, lambda: store)
    headers = {
        "X-Operator-Id": "tester",
        "X-Operator-Role": "admin",
        "Authorization": "Bearer dev-platform-key-change-me",
    }
    with TestClient(app) as client:
        yield client, headers, store


def test_health(di_client) -> None:
    client, headers, _store = di_client
    response = client.get("/decision-intelligence/health", headers=headers)
    assert response.status_code == 200
    assert response.json()["storage_backend"] == "jsonl"


def test_events_crud_and_filter(di_client) -> None:
    client, headers, _store = di_client
    create = client.post(
        "/decision-intelligence/events",
        headers=headers,
        json={
            "event_id": "evt_proxy_1",
            "domain": "endpoint_reliability",
            "title": "Proxy drift detected",
            "category": "network",
            "timestamp_utc": "2026-06-04T12:00:00Z",
        },
    )
    assert create.status_code == 201
    listed = client.get(
        "/decision-intelligence/events",
        headers=headers,
        params={"domain": "endpoint_reliability", "page": 1, "page_size": 10},
    )
    body = listed.json()
    assert body["total"] == 1
    assert body["items"][0]["event_id"] == "evt_proxy_1"


def test_decisions_outcomes_metrics_replay(di_client) -> None:
    client, headers, _store = di_client
    client.post(
        "/decision-intelligence/decisions",
        headers=headers,
        json={
            "decision_id": "dec_test_1",
            "domain": "generic",
            "title": "Preview remediation",
            "confidence": 0.7,
            "risk_score": 30.0,
            "policy_status": "PREVIEW",
            "timestamp_utc": "2026-06-04T12:00:00Z",
        },
    )
    client.post(
        "/decision-intelligence/outcomes",
        headers=headers,
        json={
            "outcome_id": "oc_test_1",
            "decision_id": "dec_test_1",
            "outcome": "Resolved",
            "success": True,
            "predicted_success": True,
            "cost": 5.0,
            "time_to_resolution": 120.0,
            "recorded_at_utc": "2026-06-04T13:00:00Z",
        },
    )
    metrics = client.get("/decision-intelligence/metrics", headers=headers)
    assert metrics.status_code == 200
    data = metrics.json()
    assert data["store"]["decisions"] == 1
    assert data["store"]["outcomes"] == 1
    assert "decision_accuracy" in data["learning"]

    replay = client.post("/decision-intelligence/replay", headers=headers, json={})
    assert replay.status_code == 200
    assert replay.json()["outcome_count"] == 1
    assert len(replay.json()["content_digest"]) == 64


def test_evidence_pagination(di_client) -> None:
    client, headers, _store = di_client
    for idx in range(3):
        client.post(
            "/decision-intelligence/evidence",
            headers=headers,
            json={
                "evidence_id": f"ev_{idx}",
                "event_id": "evt_1",
                "label": f"Evidence {idx}",
                "kind": "observation",
            },
        )
    page = client.get(
        "/decision-intelligence/evidence",
        headers=headers,
        params={"page": 1, "page_size": 2},
    )
    body = page.json()
    assert body["total"] == 3
    assert len(body["items"]) == 2
    assert body["has_more"] is True
