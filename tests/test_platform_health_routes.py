"""FastAPI liveness/readiness/metrics contract (in-process, no Docker)."""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch, tmp_path):
    monkeypatch.setenv("PLATFORM_FIXTURE_MODE", "1")
    monkeypatch.setenv("PLATFORM_SAFE_MODE", "1")
    monkeypatch.setenv("PLATFORM_DATA_DIR", str(tmp_path / "platform"))
    monkeypatch.setenv("FAIL_FAST_ON_STARTUP", "0")
    monkeypatch.delenv("PLATFORM_API_KEY", raising=False)
    os.environ.pop("PLATFORM_API_KEY", None)
    from backend.main import app

    return TestClient(app)


def test_platform_health(client: TestClient) -> None:
    r = client.get("/platform/health")
    assert r.status_code == 200
    body = r.json()
    assert body.get("status") in {"ok", "healthy", "up"}


def test_platform_ready(client: TestClient) -> None:
    r = client.get("/platform/ready")
    assert r.status_code == 200


def test_metrics_prometheus_text(client: TestClient) -> None:
    r = client.get("/metrics")
    assert r.status_code == 200
    assert "text/plain" in (r.headers.get("content-type") or "")
    assert "erp_" in r.text or "http_requests" in r.text or len(r.text) > 0
