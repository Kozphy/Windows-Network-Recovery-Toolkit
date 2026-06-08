"""Sysmon registry-write causation for proxy-watch transitions."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.correlation.process_tree import ProcessTreeBuilder
from src.correlation.proxy_causation import analyze_from_proxy_watch_row, analyze_proxy_causation
from src.proxy_guard.audit import emit_proxy_change_detected_audit, proxy_change_audit_jsonl_path
from src.reports.causation_report import render_causation_text
from src.telemetry.registry_targets import (
    details_matches_expected,
    is_proxy_registry_target,
    normalize_registry_path,
    proxy_registry_value_name,
)
from src.telemetry.sysmon_reader import parse_sysmon_xml, parse_sysmon_xml_batch, query_sysmon_events

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "sysmon"


def _load(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def _node_bundle() -> list[str]:
    return [
        _load("eid13_proxyserver_node.xml"),
        _load("eid13_proxyenable_dword1.xml"),
        _load("eid1_node_from_powershell.xml"),
        _load("eid1_powershell_parent.xml"),
        _load("eid3_listener_64394.xml"),
    ]


def test_hku_path_normalization() -> None:
    hku = (
        r"HKU\S-1-5-21-123\Software\Microsoft\Windows\CurrentVersion\Internet Settings\ProxyServer"
    )
    hkcu = r"HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings\ProxyServer"
    assert is_proxy_registry_target(hku)
    assert is_proxy_registry_target(hkcu)
    assert proxy_registry_value_name(hku) == "proxyserver"
    norm = normalize_registry_path(hkcu, user_sid="S-1-5-21-123")
    assert norm.startswith("hku\\s-1-5-21-123\\")


def test_details_matches_proxyenable_and_server() -> None:
    assert details_matches_expected("proxyenable", "DWORD (0x00000001)", 1)
    assert details_matches_expected("proxyserver", "127.0.0.1:64394", "127.0.0.1:64394")
    assert details_matches_expected("proxyserver", "(Empty)", None)


def test_parse_sysmon_eid13_proxyserver() -> None:
    ev = parse_sysmon_xml(_load("eid13_proxyserver_node.xml"))
    assert ev is not None
    assert ev.event_id == 13
    assert ev.image and "node.exe" in ev.image.lower()
    assert ev.details == "127.0.0.1:64394"


def test_final_causation_proxyserver_node() -> None:
    events = parse_sysmon_xml_batch(_node_bundle())
    result = analyze_proxy_causation(
        timestamp_utc="2026-06-08T05:00:55Z",
        before_state={"proxy_server": None, "proxy_enable": 0},
        after_state={"proxy_server": "127.0.0.1:64394", "proxy_enable": 1},
        changed_fields=["ProxyServer", "ProxyEnable"],
        observed_localhost_port=64394,
        sysmon_events=events,
    )
    assert result.causation_level == "FINAL_CAUSATION"
    assert result.writer_process and "node.exe" in result.writer_process.lower()
    assert result.confidence >= 0.9
    assert "127.0.0.1:64394" in (result.matched_registry_details or "")


def test_final_causation_proxyenable_dword() -> None:
    events = parse_sysmon_xml_batch(_node_bundle())
    result = analyze_proxy_causation(
        timestamp_utc="2026-06-08T05:00:55Z",
        before_state={"proxy_enable": 0},
        after_state={"proxy_enable": 1},
        changed_fields=["ProxyEnable"],
        sysmon_events=events,
    )
    assert result.causation_level == "FINAL_CAUSATION"
    assert proxy_registry_value_name(result.matched_registry_target or "") == "proxyenable"


def test_process_tree_powershell_parent_node() -> None:
    events = parse_sysmon_xml_batch(_node_bundle())
    builder = ProcessTreeBuilder(events)
    chain = builder.ancestor_chain("{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}")
    images = [n.get("image") or "" for n in chain]
    assert any("powershell.exe" in i.lower() for i in images)
    assert any("node.exe" in i.lower() for i in images)


def test_missing_sysmon_events_unknown() -> None:
    result = analyze_proxy_causation(
        timestamp_utc="2026-06-08T05:00:55Z",
        before_state={"proxy_enable": 0},
        after_state={"proxy_enable": 1},
        changed_fields=["ProxyEnable"],
        sysmon_events=[],
    )
    assert result.causation_level == "UNKNOWN"
    assert result.confidence <= 0.2


def test_listener_only_correlation() -> None:
    result = analyze_proxy_causation(
        timestamp_utc="2026-06-08T05:00:55Z",
        before_state={"proxy_server": None},
        after_state={"proxy_server": "127.0.0.1:64394"},
        changed_fields=["ProxyServer"],
        observed_localhost_port=64394,
        listener_process={"name": "node.exe", "pid": 12345, "parent_name": "powershell.exe"},
        sysmon_events=[],
    )
    assert result.causation_level == "CORRELATION_ONLY"
    assert "registry writer proof unavailable" in result.explanation.lower()


def test_registry_writer_without_listener() -> None:
    events = parse_sysmon_xml_batch([_load("eid13_proxyserver_node.xml")])
    result = analyze_proxy_causation(
        timestamp_utc="2026-06-08T05:00:55Z",
        before_state={"proxy_server": None},
        after_state={"proxy_server": "127.0.0.1:64394"},
        changed_fields=["ProxyServer"],
        observed_localhost_port=None,
        sysmon_events=events,
    )
    assert result.causation_level == "FINAL_CAUSATION"
    assert not result.network_events


def test_wrong_process_listening_same_port() -> None:
    events = parse_sysmon_xml_batch(
        [
            _load("eid13_proxyserver_node.xml"),
            _load("eid3_listener_64394.xml").replace("node.exe", "python.exe"),
        ]
    )
    result = analyze_proxy_causation(
        timestamp_utc="2026-06-08T05:00:55Z",
        before_state={"proxy_server": None},
        after_state={"proxy_server": "127.0.0.1:64394"},
        changed_fields=["ProxyServer"],
        observed_localhost_port=64394,
        listener_process={"name": "python.exe", "pid": 5555},
        sysmon_events=events,
    )
    assert result.causation_level == "FINAL_CAUSATION"
    assert result.writer_process and "node.exe" in result.writer_process.lower()


def test_multiple_changes_short_window() -> None:
    events = parse_sysmon_xml_batch(_node_bundle())
    r1 = analyze_proxy_causation(
        timestamp_utc="2026-06-08T05:00:55Z",
        before_state={"proxy_enable": 0},
        after_state={"proxy_enable": 1},
        changed_fields=["ProxyEnable"],
        sysmon_events=events,
    )
    r2 = analyze_proxy_causation(
        timestamp_utc="2026-06-08T05:00:55Z",
        before_state={"proxy_server": None},
        after_state={"proxy_server": "127.0.0.1:64394"},
        changed_fields=["ProxyServer"],
        sysmon_events=events,
    )
    assert r1.causation_level == "FINAL_CAUSATION"
    assert r2.causation_level == "FINAL_CAUSATION"


def test_proxyserver_cleared_strong_or_final() -> None:
    events = parse_sysmon_xml_batch([_load("eid13_proxyserver_cleared.xml")])
    result = analyze_proxy_causation(
        timestamp_utc="2026-06-08T05:01:10Z",
        before_state={"proxy_server": "127.0.0.1:64394"},
        after_state={"proxy_server": None},
        changed_fields=["ProxyServer"],
        sysmon_events=events,
    )
    assert result.causation_level in ("FINAL_CAUSATION", "STRONG_CAUSATION")
    assert result.writer_process and "reg.exe" in result.writer_process.lower()


def test_nvidia_python_low_confidence_without_registry() -> None:
    result = analyze_proxy_causation(
        timestamp_utc="2026-06-08T05:00:55Z",
        before_state={"proxy_server": None},
        after_state={"proxy_server": "127.0.0.1:64394"},
        changed_fields=["ProxyServer"],
        observed_localhost_port=64394,
        listener_process={
            "name": "python.exe",
            "pid": 7777,
            "command_line": "python -m nvidia_smi_proxy",
        },
        sysmon_events=[],
    )
    assert result.causation_level == "CORRELATION_ONLY"
    assert result.confidence <= 0.3


def test_analyze_from_proxy_watch_row(tmp_path: Path) -> None:
    row = {
        "timestamp": "2026-06-08T05:00:55Z",
        "diff": {
            "before": {"proxy_server": None, "proxy_enable": 0},
            "after": {"proxy_server": "127.0.0.1:64394", "proxy_enable": 1},
            "changed_fields": ["ProxyServer", "ProxyEnable"],
        },
        "attribution": {
            "primary_suspect": {"name": "node.exe", "pid": 12345, "parent_name": "powershell.exe"},
        },
    }
    events = parse_sysmon_xml_batch(_node_bundle())
    result = analyze_from_proxy_watch_row(row, sysmon_events=events)
    assert result.causation_level == "FINAL_CAUSATION"


def test_emit_audit_with_causation(tmp_path: Path) -> None:
    emit_proxy_change_detected_audit(
        tmp_path,
        diff={"changed": True, "risk_level": "high"},
        attribution={"confidence": 0.8},
        decision={"action": "alert", "reason": "high_risk"},
        causation={"causation_level": "FINAL_CAUSATION", "writer_process": "node.exe"},
    )
    path = proxy_change_audit_jsonl_path(tmp_path)
    row = json.loads(path.read_text(encoding="utf-8").strip())
    assert row["causation"]["causation_level"] == "FINAL_CAUSATION"


def test_render_causation_report() -> None:
    events = parse_sysmon_xml_batch(_node_bundle())
    result = analyze_proxy_causation(
        timestamp_utc="2026-06-08T05:00:55Z",
        before_state={"proxy_server": None},
        after_state={"proxy_server": "127.0.0.1:64394"},
        changed_fields=["ProxyServer"],
        sysmon_events=events,
    )
    text = render_causation_text(result, transition_summary="ProxyServer drift")
    assert "Final causation found" in text
    assert "node.exe" in text.lower()


def test_query_sysmon_injectable_xml() -> None:
    docs = [_load("eid13_proxyserver_node.xml")]
    events = query_sysmon_events(
        __import__("datetime").datetime(2026, 6, 8, tzinfo=__import__("datetime").timezone.utc),
        __import__("datetime").datetime(2026, 6, 8, 1, tzinfo=__import__("datetime").timezone.utc),
        xml_documents=docs,
    )
    assert len(events) == 1


def test_cmd_proxy_forensics_cli(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    from argparse import Namespace

    from src.command_handlers import cmd_proxy_forensics

    emit_proxy_change_detected_audit(
        tmp_path,
        diff={
            "changed": True,
            "risk_level": "high",
            "before": {"proxy_server": None, "proxy_enable": 0},
            "after": {"proxy_server": "127.0.0.1:64394", "proxy_enable": 1},
            "changed_fields": ["ProxyServer", "ProxyEnable"],
        },
        attribution={"primary_suspect": {"name": "node.exe", "pid": 1}},
        decision={"action": "alert", "reason": "high"},
    )

    events = parse_sysmon_xml_batch(_node_bundle())
    monkeypatch.setattr(
        "src.correlation.proxy_causation.query_sysmon_events",
        lambda *a, **k: events,
    )

    args = Namespace(
        repo_root=tmp_path,
        emit_json=True,
        forensics_since_minutes=30,
        forensics_around=None,
        forensics_window_seconds=10,
        forensics_watch_integrated=True,
    )
    code = cmd_proxy_forensics(args)
    assert code == 0
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert payload["transitions_analyzed"] >= 1
    assert payload["results"][0]["causation"]["causation_level"] == "FINAL_CAUSATION"
