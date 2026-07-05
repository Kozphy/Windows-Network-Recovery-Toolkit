"""Security abuse case tests."""

from __future__ import annotations

from fastapi.testclient import TestClient

from backend.main import app
from src.platform_core.ai_risk_analyst.explanation_guardrails import validate_explanation_text

client = TestClient(app)


def test_malware_language_blocked_in_ai():
    result = validate_explanation_text("malware confirmed on endpoint")
    assert not result.is_safe


def test_duplicate_ingest_same_hash(sample_proxy_evidence, auth_headers):
    r1 = client.post("/v1/evidence", json=sample_proxy_evidence, headers=auth_headers)
    r2 = client.post("/v1/evidence", json=sample_proxy_evidence, headers=auth_headers)
    assert r1.json()["event_id"] == r2.json()["event_id"]


def test_no_remediation_post_on_v1(auth_headers):
    r = client.post("/v1/incidents/INC-FAKE/remediate", headers=auth_headers)
    assert r.status_code in (404, 405, 422)
