from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def plat_client(monkeypatch, tmp_path):
    def target() -> object:
        return tmp_path

    monkeypatch.setattr("platform_core.storage.platform_data_dir", target)
    monkeypatch.setattr("platform_core.event_bus.platform_data_dir", target)

    from backend.main import app

    return TestClient(
        app,
        headers={
            "X-Operator-Role": "admin",
            "X-Operator-Id": "pytest-production",
        },
    )


def test_prometheus_metrics_endpoint(plat_client: TestClient) -> None:
    r = plat_client.get("/metrics")
    assert r.status_code == 200
    assert "platform_http_requests_total" in r.text


def test_platform_probes_route(plat_client: TestClient) -> None:
    r = plat_client.get("/platform/probes")
    assert r.status_code == 200
    body = r.json()
    assert "os_family" in body
    assert "observations" in body
    assert "epistemic_note" in body


def test_platform_ready_after_startup(plat_client: TestClient) -> None:
    r = plat_client.get("/platform/ready")
    assert r.status_code == 200
    body = r.json()
    assert body.get("ok") is True
    assert isinstance(body.get("checks"), list)


def test_correlation_run_preview_only(plat_client: TestClient) -> None:
    r = plat_client.post(
        "/platform/correlation/run",
        json={
            "endpoint_id": "local-test",
            "requested_action": "inspect_proxy",
            "signals": [{"signal_name": "proxy_enabled", "value": True}],
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body.get("dry_run_only") is True
    assert "evidence_tree" in body


def test_correlation_run_with_probe(plat_client: TestClient) -> None:
    r = plat_client.post(
        "/platform/correlation/run",
        json={"endpoint_id": "probe-test", "use_probe": True},
    )
    assert r.status_code == 200
    assert r.json().get("correlation_id")


def test_events_recent_merge(plat_client: TestClient) -> None:
    r = plat_client.get("/platform/events/recent?limit=5")
    assert r.status_code == 200
    body = r.json()
    assert "items" in body
    assert "normalized_count" in body


def test_platform_api_key_auth(monkeypatch, tmp_path) -> None:
    from platform_core.settings import reset_settings_cache

    monkeypatch.setenv("PLATFORM_API_KEY", "test-secret-key")
    reset_settings_cache()

    def target() -> object:
        return tmp_path

    monkeypatch.setattr("platform_core.storage.platform_data_dir", target)
    monkeypatch.setattr("platform_core.event_bus.platform_data_dir", target)

    from backend.main import app

    bad = TestClient(app, headers={"Authorization": "Bearer wrong"})
    assert bad.get("/platform/probes").status_code == 401

    good = TestClient(app, headers={"Authorization": "Bearer test-secret-key"})
    assert good.get("/platform/probes").status_code == 200
