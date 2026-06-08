"""Integration tests for /platform/v2/sre API."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def sre_client(monkeypatch: pytest.MonkeyPatch, tmp_path) -> TestClient:
    monkeypatch.setattr("platform_core.storage.platform_data_dir", lambda: tmp_path)
    monkeypatch.setattr("platform_core.event_bus.platform_data_dir", lambda: tmp_path)
    from platform_core.sre.failure_domains import reset_domains_for_tests

    reset_domains_for_tests()
    from backend.main import app

    return TestClient(
        app,
        headers={"X-Operator-Role": "admin", "X-Operator-Id": "pytest-sre"},
    )


def test_sre_open_investigate_resolve_postmortem(sre_client: TestClient) -> None:
    opened = sre_client.post(
        "/platform/v2/sre/incidents",
        json={"endpoint_id": "ep-1", "title": "proxy drift", "severity": "high"},
    )
    assert opened.status_code == 200
    incident_id = opened.json()["incident_id"]

    inv = sre_client.post(
        f"/platform/v2/sre/incidents/{incident_id}/investigate",
        json={
            "observations": [
                {"signal_name": "wininet_proxy_enabled", "value": 1},
                {"signal_name": "localhost_proxy_detected"},
            ],
        },
    )
    assert inv.status_code == 200
    assert inv.json()["status"] == "ok"

    timeline = sre_client.get(f"/platform/v2/sre/incidents/{incident_id}/timeline")
    assert timeline.status_code == 200
    assert len(timeline.json()["entries"]) >= 3

    resolved = sre_client.post(
        f"/platform/v2/sre/incidents/{incident_id}/resolve",
        json={"resolution": "listener stopped"},
    )
    assert resolved.status_code == 200
    assert resolved.json()["phase"] == "RESOLVED"

    pm = sre_client.post(f"/platform/v2/sre/incidents/{incident_id}/postmortem")
    assert pm.status_code == 200
    assert "Postmortem" in pm.json()["markdown"]

    mttr = sre_client.get("/platform/v2/sre/metrics/mttr")
    assert mttr.status_code == 200
    assert mttr.json()["metrics"]["resolved_count"] == 1
