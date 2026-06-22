"""Policy bypass attempts blocked."""

from __future__ import annotations

from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_operator_cannot_post_fake_execute():
    headers = {"X-Api-Token": "test-token", "X-Api-Role": "admin"}
    r = client.post("/v1/remediation/execute", headers=headers, json={"action": "kill_process"})
    assert r.status_code in (404, 405, 422)
