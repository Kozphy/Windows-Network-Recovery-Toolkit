"""Ensure API responses do not leak tokens."""

from __future__ import annotations

from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_401_does_not_echo_token(sample_proxy_evidence):
    r = client.post(
        "/v1/evidence",
        json=sample_proxy_evidence,
        headers={"X-Api-Token": "super-secret-token"},
    )
    assert r.status_code == 401
    assert "super-secret-token" not in r.text
