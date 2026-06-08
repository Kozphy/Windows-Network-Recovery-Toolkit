"""Integration tests for /platform/v2 reliability API."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def v2_client(monkeypatch: pytest.MonkeyPatch, tmp_path) -> TestClient:
    def target():
        return tmp_path
    monkeypatch.setattr("platform_core.storage.platform_data_dir", target)
    monkeypatch.setattr("platform_core.event_bus.platform_data_dir", target)
    from backend.main import app

    return TestClient(
        app,
        headers={"X-Operator-Role": "admin", "X-Operator-Id": "pytest-v2"},
    )


def test_v2_health(v2_client: TestClient) -> None:
    r = v2_client.get("/platform/v2/health")
    assert r.status_code == 200
    body = r.json()
    assert body["api_version"] == "v2"
    assert "observation_ne_proof" in body["principles"]


def test_v2_decision_run_preview(v2_client: TestClient) -> None:
    r = v2_client.post(
        "/platform/v2/decisions/run",
        json={
            "endpoint_id": "pytest-ep",
            "observations": [
                {"signal_name": "wininet_proxy_enabled", "value": 1},
                {"signal_name": "localhost_proxy_detected"},
            ],
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["policy_outcome"] == "PREVIEW"
    assert "LOCAL_PROXY_ENABLED" in body["state_path"]
    assert body.get("audit_signature")


def test_v2_replay_parity(v2_client: TestClient) -> None:
    run = v2_client.post(
        "/platform/v2/decisions/run",
        json={
            "observations": [
                {"source_kind": "registry", "signal_name": "wininet_proxy_enabled", "value": 1},
                {"source_kind": "network_telemetry", "signal_name": "localhost_proxy_detected"},
            ],
        },
    ).json()
    run_id = run["run_id"]
    replay = v2_client.get(f"/platform/v2/decisions/replay/{run_id}")
    assert replay.status_code == 200
    parity = replay.json()["parity"]
    assert parity["policy_outcome"] is True
    assert parity["state_path"] is True


def test_v2_policies_summary(v2_client: TestClient) -> None:
    r = v2_client.get("/platform/v2/policies/summary")
    assert r.status_code == 200
    assert r.json()["default_outcome"] == "PREVIEW"
