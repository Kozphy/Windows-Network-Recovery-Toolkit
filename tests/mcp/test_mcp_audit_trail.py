"""MCP audit trail tests."""

from __future__ import annotations

from mcp_server import tools
from src.platform_core.events import TriskEventType, reset_event_store


def test_tool_invocation_creates_mcp_event(tmp_path, monkeypatch):
    monkeypatch.setenv("PLATFORM_DATA_DIR", str(tmp_path))
    reset_event_store()
    tools.get_evidence_timeline("evt-test-1")
    from src.platform_core.events import get_event_store

    events = list(get_event_store().iter_events(aggregate_id="mcp:session", limit=10))
    assert len(events) >= 1
    assert events[0].event_type == TriskEventType.MCP_TOOL_INVOKED
    assert events[0].payload.get("read_only") is True
