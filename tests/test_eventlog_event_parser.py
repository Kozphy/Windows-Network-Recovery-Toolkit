"""Tests for Windows Event Log parser abstraction."""

from __future__ import annotations

import json
from pathlib import Path

from telemetry.eventlog_reader import parse_windows_registry_event, query_windows_eventlog_preview

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "telemetry"


def test_parse_windows_registry_event_from_sysmon_fixture() -> None:
    raw = json.loads(
        (FIXTURES / "sysmon_event13_proxy_enable_node.json").read_text(encoding="utf-8")
    )
    event = parse_windows_registry_event(raw)
    assert event is not None
    assert event.source == "windows_eventlog"
    assert event.registry_value_name == "ProxyEnable"


def test_query_windows_eventlog_preview_non_windows_safe() -> None:
    rows = query_windows_eventlog_preview(since_seconds=60)
    assert isinstance(rows, list)


def test_irrelevant_eventlog_row_returns_none() -> None:
    assert (
        parse_windows_registry_event({"EventID": 4624, "ObjectName": "HKLM\\System\\Demo"}) is None
    )
