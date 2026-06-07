"""Tests for Sysmon registry event parser."""

from __future__ import annotations

import json
from pathlib import Path

from telemetry.sysmon_reader import (
    is_relevant_proxy_registry_path,
    normalize_registry_path,
    parse_sysmon_registry_event,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "telemetry"


def test_parse_sysmon_proxy_enable_fixture() -> None:
    raw = json.loads(
        (FIXTURES / "sysmon_event13_proxy_enable_node.json").read_text(encoding="utf-8")
    )
    event = parse_sysmon_registry_event(raw)
    assert event is not None
    assert event.event_id == 13
    assert event.process_id == 21712
    assert event.registry_value_name == "ProxyEnable"
    assert event.process_name == "node.exe"


def test_parse_sysmon_proxy_server_fixture() -> None:
    raw = json.loads(
        (FIXTURES / "sysmon_event13_proxy_server_node.json").read_text(encoding="utf-8")
    )
    event = parse_sysmon_registry_event(raw)
    assert event is not None
    assert event.registry_value_data == "127.0.0.1:63722"


def test_missing_fields_do_not_crash() -> None:
    raw = json.loads((FIXTURES / "missing_fields.json").read_text(encoding="utf-8"))
    event = parse_sysmon_registry_event(raw)
    assert event is not None
    assert event.process_id is None
    assert "missing_process_id" in event.parse_warnings
    assert "missing_image" in event.parse_warnings


def test_non_proxy_registry_path_ignored() -> None:
    raw = {
        "EventID": 13,
        "TargetObject": r"HKCU\Software\Demo\App\Setting",
        "Image": r"C:\Windows\System32\cmd.exe",
        "ProcessId": 1,
        "UtcTime": "2026-01-15T12:00:05Z",
    }
    event = parse_sysmon_registry_event(raw)
    assert event is not None
    assert not is_relevant_proxy_registry_path(event.registry_path)


def test_normalize_registry_path_hkcu_alias() -> None:
    path = normalize_registry_path(
        r"HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Internet Settings\ProxyServer"
    )
    assert path.startswith("HKCU\\")


def test_non_sysmon_event_returns_none() -> None:
    assert parse_sysmon_registry_event({"EventID": 1}) is None
