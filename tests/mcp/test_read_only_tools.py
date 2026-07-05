"""MCP read-only tool tests."""

from __future__ import annotations

import pytest

from mcp_server import tools
from src.platform_core.events import reset_event_store


@pytest.fixture(autouse=True)
def _env(tmp_path, monkeypatch):
    monkeypatch.setenv("PLATFORM_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("MCP_READ_ONLY", "1")
    reset_event_store()
    yield


def test_get_proxy_status_fixture():
    result = tools.get_proxy_status("fixtures/proxy/dead-localhost-proxy.json")
    assert "limitations" in result or "wininet" in str(result).lower()


def test_generate_governance_report():
    report = tools.generate_governance_report("tests/fixtures/risk_analytics/audit_sample")
    assert "limitations" in report


def test_mcp_audit_event_appended():
    tools.get_risk_report(limit=5)
    events = tools.list_events_tool(limit=5)
    assert any(e.get("event_type") == "McpToolInvoked" for e in events["items"])
