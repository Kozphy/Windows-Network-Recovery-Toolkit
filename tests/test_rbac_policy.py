from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def rbac_app(monkeypatch, tmp_path):
    monkeypatch.setattr("platform_core.storage.platform_data_dir", lambda: tmp_path)
    from backend.main import app

    return app


def test_viewer_cannot_remediation_preview(rbac_app) -> None:
    admin = TestClient(rbac_app, headers={"X-Operator-Role": "admin", "X-Operator-Id": "a1"})
    admin.post(
        "/platform/failure-events/ingest",
        json={
            "event_id": "rbac-ev-1",
            "endpoint_id": "rbac-ep",
            "severity": "low",
            "category": "dns",
            "confidence": 0.5,
            "summary": "x",
            "recommended_action_key": "reset_dns",
        },
    )
    viewer = TestClient(rbac_app, headers={"X-Operator-Role": "viewer", "X-Operator-Id": "v1"})
    r = viewer.post(
        "/platform/remediation/preview",
        json={
            "endpoint_id": "rbac-ep",
            "failure_event_id": "rbac-ev-1",
            "requested_action": "reset_dns",
        },
    )
    assert r.status_code == 403


def test_operator_cannot_live_execute(rbac_app) -> None:
    admin = TestClient(rbac_app, headers={"X-Operator-Role": "admin", "X-Operator-Id": "a2"})
    admin.post(
        "/platform/failure-events/ingest",
        json={
            "event_id": "rbac-ev-2",
            "endpoint_id": "rbac-ep2",
            "severity": "low",
            "category": "dns",
            "confidence": 0.5,
            "summary": "x",
            "recommended_action_key": "reset_dns",
        },
    )
    prv = admin.post(
        "/platform/remediation/preview",
        json={
            "endpoint_id": "rbac-ep2",
            "failure_event_id": "rbac-ev-2",
            "requested_action": "reset_dns",
        },
    )
    pid = prv.json()["preview_id"]

    op = TestClient(rbac_app, headers={"X-Operator-Role": "operator", "X-Operator-Id": "o1"})
    r = op.post(
        "/platform/remediation/execute",
        json={
            "preview_id": pid,
            "confirmation_phrase": "RUN_DNS_RESET",
            "dry_run": False,
        },
    )
    assert r.status_code == 403


def test_security_auditor_reads_audit(rbac_app) -> None:
    aud = TestClient(
        rbac_app,
        headers={"X-Operator-Role": "security_auditor", "X-Operator-Id": "audit1"},
    )
    assert aud.get("/platform/audit").status_code == 200


def test_viewer_cannot_read_audit(rbac_app) -> None:
    v = TestClient(rbac_app, headers={"X-Operator-Role": "viewer", "X-Operator-Id": "v2"})
    assert v.get("/platform/audit").status_code == 403
