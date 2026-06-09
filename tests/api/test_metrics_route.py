"""Metrics route test."""

from __future__ import annotations

from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_metrics_shape() -> None:
    r = client.get("/v1/metrics")
    assert r.status_code == 200
    body = r.json()
    assert "outcomes" in body
    assert "slo" in body
