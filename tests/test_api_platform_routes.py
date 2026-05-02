from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def plat_client(monkeypatch, tmp_path):
    monkeypatch.setattr("platform_core.storage.platform_data_dir", lambda: tmp_path)

    from backend.main import app

    return TestClient(
        app,
        headers={
            "X-Operator-Role": "admin",
            "X-Operator-Id": "pytest-platform",
        },
    )


def test_platform_health(plat_client: TestClient) -> None:
    r = plat_client.get("/platform/health")
    assert r.status_code == 200
    body = r.json()
    assert body.get("status") == "ok"
    assert "safe_mode" in body


def test_failure_event_ingest_and_preview_execute_dry_run(plat_client: TestClient) -> None:
    evt = {
        "event_id": "api-test-ev-1",
        "endpoint_id": "api-test-ep",
        "severity": "medium",
        "category": "dns",
        "confidence": 0.82,
        "summary": "api fixture",
        "recommended_action_key": "reset_dns",
    }
    r1 = plat_client.post("/platform/failure-events/ingest", json=evt)
    assert r1.status_code == 200

    prv = plat_client.post(
        "/platform/remediation/preview",
        json={
            "endpoint_id": "api-test-ep",
            "failure_event_id": "api-test-ev-1",
            "requested_action": "reset_dns",
        },
    )
    assert prv.status_code == 200
    preview_id = prv.json().get("preview_id")
    assert preview_id

    ex = plat_client.post(
        "/platform/remediation/execute",
        json={"preview_id": preview_id, "confirmation_phrase": "RUN_DNS_RESET", "dry_run": True},
    )
    assert ex.status_code == 200
    assert ex.json().get("result") == "dry_run"


def test_get_failure_event_includes_linked_block_payload(plat_client: TestClient) -> None:
    evt = {
        "event_id": "api-linked-1",
        "endpoint_id": "api-test-ep",
        "failure_block_id": "00000000-0000-0000-0000-000000000099",
        "severity": "low",
        "category": "dns",
        "confidence": 0.5,
        "summary": "fixture linkage",
        "recommended_action_key": "inspect_proxy",
    }
    plat_client.post("/platform/failure-events/ingest", json=evt)
    r = plat_client.get("/platform/failure-events/api-linked-1")
    assert r.status_code == 200
    body = r.json()
    assert body.get("failure_event", {}).get("event_id") == "api-linked-1"
    linked = body.get("failure_block_linked") or {}
    assert linked.get("found") is False
    assert linked.get("failure_block_id") == "00000000-0000-0000-0000-000000000099"


def test_high_risk_execute_blocked_via_policy_layers(plat_client: TestClient) -> None:
    evt = {
        "event_id": "api-fw-1",
        "endpoint_id": "api-test-ep",
        "severity": "high",
        "category": "firewall",
        "confidence": 0.9,
        "summary": "fixture",
        "recommended_action_key": "reset_firewall",
    }
    plat_client.post("/platform/failure-events/ingest", json=evt)
    prv = plat_client.post(
        "/platform/remediation/preview",
        json={
            "endpoint_id": "api-test-ep",
            "failure_event_id": "api-fw-1",
            "requested_action": "reset_firewall",
        },
    )
    prv_body = prv.json()
    preview_id = prv_body["preview_id"]
    assert prv_body.get("allowed_by_policy") is False
    ex = plat_client.post(
        "/platform/remediation/execute",
        json={"preview_id": preview_id, "confirmation_phrase": "RUN_FIREWALL_RESET", "dry_run": False},
    )
    assert ex.status_code == 200
    assert ex.json().get("result") == "blocked"

