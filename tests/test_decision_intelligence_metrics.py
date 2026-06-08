from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.decision_intelligence.metrics import reset_for_tests
from backend.decision_intelligence.store import JsonlDecisionIntelligenceStore, reset_store
from backend.main import app


@pytest.fixture
def metrics_client(tmp_path, monkeypatch):
    reset_for_tests()
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
        "X-Operator-Id": "metrics-tester",
        "X-Operator-Role": "admin",
        "Authorization": "Bearer dev-platform-key-change-me",
    }
    with TestClient(app) as client:
        yield client, headers


def test_prometheus_exposes_decision_intelligence_metrics(metrics_client) -> None:
    client, headers = metrics_client
    client.post(
        "/decision-intelligence/events",
        headers=headers,
        json={
            "event_id": "evt_m1",
            "domain": "generic",
            "title": "Test event",
            "timestamp_utc": "2026-06-04T12:00:00Z",
        },
    )
    client.post(
        "/decision-intelligence/decisions",
        headers=headers,
        json={
            "decision_id": "dec_m1",
            "domain": "generic",
            "title": "Test decision",
            "confidence": 0.8,
            "risk_score": 10.0,
            "timestamp_utc": "2026-06-04T12:00:00Z",
        },
    )
    client.post(
        "/decision-intelligence/outcomes",
        headers=headers,
        json={
            "outcome_id": "oc_m1",
            "decision_id": "dec_m1",
            "outcome": "failed path",
            "success": False,
            "predicted_success": True,
            "recorded_at_utc": "2026-06-04T13:00:00Z",
        },
    )
    client.get("/decision-intelligence/metrics", headers=headers)

    prom = client.get("/metrics")
    assert prom.status_code == 200
    text = prom.text
    assert "events_total 1" in text
    assert "decisions_total 1" in text
    assert "decision_failures 1" in text
    assert "decision_accuracy" in text
    assert "decision_latency_seconds" in text
