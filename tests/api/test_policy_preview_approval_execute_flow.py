"""Policy preview approval execute flow."""

from __future__ import annotations

from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_preview_approve_execute_blocked_without_token() -> None:
    ev = client.post("/v1/events", json={"signals": {"wininet_proxy_enabled": True}})
    assert ev.status_code == 200
    decision_id = ev.json()["decision_id"]

    preview = client.post("/v1/remediation/preview")
    assert preview.status_code == 200

    bad = client.post("/v1/remediation/execute", json={"decision_id": decision_id, "approval_token": "bad"})
    assert bad.json().get("executed") is False
