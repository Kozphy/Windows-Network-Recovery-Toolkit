"""API hardening contract — dry-run default, shell injection blocked, audit append."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def plat_client(monkeypatch, tmp_path):
    monkeypatch.setattr("platform_core.storage.platform_data_dir", lambda: tmp_path)
    monkeypatch.setattr("platform_core.event_bus.platform_data_dir", lambda: tmp_path)
    from backend.main import app

    return TestClient(app, headers={"X-Operator-Role": "admin", "X-Operator-Id": "hardening-contract"})


def test_shell_injection_action_rejected_at_preview(plat_client: TestClient) -> None:
    plat_client.post(
        "/platform/failure-events/ingest",
        json={
            "event_id": "inj-1",
            "endpoint_id": "ep-1",
            "severity": "high",
            "category": "proxy",
            "confidence": 0.9,
            "summary": "injection test",
            "recommended_action_key": "reset_proxy",
        },
    )
    r = plat_client.post(
        "/platform/remediation/preview",
        json={
            "endpoint_id": "ep-1",
            "failure_event_id": "inj-1",
            "requested_action": "reset_dns; malicious",
        },
    )
    assert r.status_code == 400


def test_preview_and_execute_append_audit(plat_client: TestClient, monkeypatch) -> None:
    plat_client.post(
        "/platform/failure-events/ingest",
        json={
            "event_id": "aud-1",
            "endpoint_id": "ep-audit",
            "severity": "low",
            "category": "dns",
            "confidence": 0.8,
            "summary": "audit trail",
            "recommended_action_key": "reset_dns",
        },
    )
    prv = plat_client.post(
        "/platform/remediation/preview",
        json={
            "endpoint_id": "ep-audit",
            "failure_event_id": "aud-1",
            "requested_action": "reset_dns",
        },
    )
    assert prv.status_code == 200
    preview_id = prv.json()["preview_id"]

    monkeypatch.setattr(
        "backend.platform_routes.subprocess.run",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("no subprocess")),
    )
    ex = plat_client.post(
        "/platform/remediation/execute",
        json={"preview_id": preview_id, "confirmation_phrase": "RUN_DNS_RESET"},
    )
    assert ex.status_code == 200
    assert ex.json().get("dry_run") is True

    tail = plat_client.get("/platform/audit/tail?limit=20")
    assert tail.status_code == 200
    items = tail.json().get("items") or []
    actions = {row.get("action") for row in items}
    assert "remediation_preview" in actions or "remediation_execute" in actions
