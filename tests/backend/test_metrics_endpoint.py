"""Metrics endpoint tests."""

from __future__ import annotations

from fastapi.testclient import TestClient

from backend.main import app
from backend.trisk_metrics import inc

client = TestClient(app)


def test_metrics_includes_trisk_counters():
    inc("evidence_events_ingested_total")
    inc("domain_events_appended_total", labels={"event_type": "EvidenceCollected"})
    inc("mcp_tool_invocations_total", labels={"tool": "get_risk_report"})
    r = client.get("/metrics")
    assert r.status_code == 200
    assert "evidence_events_ingested_total" in r.text or "platform_http_requests_total" in r.text
    assert "domain_events_appended_total" in r.text
    assert "mcp_tool_invocations_total" in r.text
