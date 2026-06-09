"""Canonical API route tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


@pytest.mark.parametrize(
    "method,path",
    [
        ("GET", "/v1/health"),
        ("GET", "/v1/version"),
        ("GET", "/v1/metrics"),
        ("GET", "/v1/governance/controls"),
    ],
)
def test_canonical_routes_not_404(method: str, path: str) -> None:
    r = client.get(path) if method == "GET" else client.post(path, json={})
    assert r.status_code != 404


def test_events_flow() -> None:
    r = client.post("/v1/events", json={"fixture_path": "proxy_drift_incident.jsonl"})
    assert r.status_code == 200
    body = r.json()
    assert "decision_id" in body
