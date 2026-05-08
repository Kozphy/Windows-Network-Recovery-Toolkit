"""Offline layered registry attribution merges (Sysmon / Procmon / listener / heuristic)."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.proxy_guard.attribution import heuristic_attribution_to_audit_dict
from src.proxy_guard.attribution_engine import attribute_proxy_change, layered_to_heuristic_pipeline
from src.proxy_guard.attribution_model import AttributionEvidence, LayeredAttributionResult, ProxyActor
from src.proxy_guard.procmon_import import load_procmon_proxy_events
from src.proxy_guard.sysmon_attribution import (
    attribution_evidence_from_sysmon_message,
    parse_sysmon_e13_message,
    proxy_target_from_sysmon_fields,
)


_SAMPLE_SYSMON_MESSAGE = """Registry value set:
RuleName: technique_id=T1112
EventType: SetValue
UtcTime: 2026-05-02 12:34:56.789
ProcessGuid: {...}
ProcessId: 1234
Image: C:\\Program Files\\SomeApp\\SomeUpdater.exe
User: COMPUTERNAME\\alice
TargetObject: HKU\\S-1-5-21-xxxxxxxx\\Software\\Microsoft\\Windows\\CurrentVersion\\Internet Settings\\ProxyServer
Details: 127.0.0.1:55509
"""


def test_parse_sysmon_e13_extracts_pairs() -> None:
    fld = parse_sysmon_e13_message(_SAMPLE_SYSMON_MESSAGE)
    assert fld.get("processid") == "1234"
    assert "SomeUpdater.exe" in (fld.get("image") or "")


def test_proxy_target_detection_from_sysmon_fields() -> None:
    fld = parse_sysmon_e13_message(_SAMPLE_SYSMON_MESSAGE)
    vk, tgt = proxy_target_from_sysmon_fields(fld)
    assert vk == "proxyserver"
    assert "Internet Settings" in tgt


def test_attribution_evidence_from_sysmon_message_builds_actor_raw() -> None:
    ev = attribution_evidence_from_sysmon_message(_SAMPLE_SYSMON_MESSAGE, time_created_hint="t")
    assert ev is not None
    assert ev.source == "sysmon_event_13"
    assert ev.confidence_score >= 0.9
    assert ev.raw_excerpt and ev.raw_excerpt.get("process_id") == 1234


def test_procmon_row_import(tmp_path: Path) -> None:
    csv_text = (
        "Time of Day,Process Name,PID,Operation,Path,Result,Detail\n"
        "12:34:56.789,svc.exe,99,RegSetValue,HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Internet Settings\\ProxyEnable,SUCCESS,DWORD:00000001\n"
    )
    p = tmp_path / "proc.csv"
    p.write_text(csv_text, encoding="utf-8")
    hits = load_procmon_proxy_events(str(p), since_seconds=None)
    assert hits
    top = hits[0]
    assert top.source == "procmon_csv"
    assert top.raw_excerpt is not None
    raw = top.raw_excerpt or {}
    assert raw.get("pid") == 99


def test_parse_proxy_multi_scheme_localhost_ports() -> None:
    from src.proxy_guard.parser import parse_proxy_server

    p = parse_proxy_server("http=127.0.0.1:88;https=127.0.0.1:443")
    assert p.http_localhost_port == 88
    assert p.https_localhost_port == 443
    socks = parse_proxy_server("socks=127.0.0.1:1080")
    assert socks.socks_port == 1080


def test_sysmon_priority_over_listener(monkeypatch: pytest.MonkeyPatch) -> None:
    sys_ev = attribution_evidence_from_sysmon_message(_SAMPLE_SYSMON_MESSAGE)
    assert sys_ev is not None

    def fake_sysmon(**_kw):
        return [sys_ev]

    listener_layer = LayeredAttributionResult(
        candidate_actor=ProxyActor(pid=4242, process_name="node.exe"),
        attribution_confidence="medium",
        attribution_method="localhost_listener",
        evidence=[],
        attribution_notes=[],
    )

    monkeypatch.setattr("src.proxy_guard.attribution_engine.collect_sysmon_proxy_events", fake_sysmon)

    monkeypatch.setattr(
        "src.proxy_guard.attribution_engine.load_procmon_proxy_events",
        lambda *a, **k: [],
    )

    monkeypatch.setattr(
        "src.proxy_guard.attribution_engine.attribute_localhost_proxy_listener",
        lambda *a, **k: listener_layer,
    )

    monkeypatch.setattr(
        "src.proxy_guard.attribution_engine.collect_recent_process_inventory",
        lambda **k: [],
    )

    old = {"proxy_enable": 0, "proxy_server": None, "auto_config_url": "", "auto_detect": 0, "proxy_override": ""}
    new = {
        "proxy_enable": 1,
        "proxy_server": "127.0.0.1:55509",
        "auto_config_url": "",
        "auto_detect": 0,
        "proxy_override": "",
    }
    out = attribute_proxy_change(old, new, since_seconds=60, evidence_csv=None, run=None)
    assert out.attribution_method == "sysmon_event_13"
    assert out.attribution_confidence == "high"
    assert out.candidate_actor is not None
    assert out.candidate_actor.pid == 1234


def test_engine_unknown_when_no_actor_evidence(monkeypatch: pytest.MonkeyPatch) -> None:
    dead_listener = LayeredAttributionResult(
        candidate_actor=None,
        attribution_confidence="unknown",
        attribution_method="unknown",
        evidence=[
            AttributionEvidence(
                source="localhost_listener",
                confidence_score=0.0,
                notes=["nothing listening"],
            ),
        ],
        attribution_notes=["no_listen"],
    )
    monkeypatch.setattr(
        "src.proxy_guard.attribution_engine.collect_sysmon_proxy_events",
        lambda **kw: [],
    )
    monkeypatch.setattr(
        "src.proxy_guard.attribution_engine.load_procmon_proxy_events",
        lambda *a, **k: [],
    )
    monkeypatch.setattr(
        "src.proxy_guard.attribution_engine.attribute_localhost_proxy_listener",
        lambda *a, **k: dead_listener,
    )
    monkeypatch.setattr(
        "src.proxy_guard.attribution_engine.collect_recent_process_inventory",
        lambda **k: [],
    )
    empty_old = {"proxy_enable": 0, "proxy_server": "", "auto_config_url": "", "auto_detect": 0, "proxy_override": ""}
    empty_new = dict(empty_old)
    out = attribute_proxy_change(empty_old, empty_new, since_seconds=30, evidence_csv=None, run=None)
    assert out.attribution_confidence == "unknown"
    assert out.candidate_actor is None


def test_pipeline_audit_includes_evidence_array() -> None:
    layered = LayeredAttributionResult(
        candidate_actor=ProxyActor(pid=9, process_name="n.exe"),
        attribution_confidence="low",
        attribution_method="process_inventory_heuristic",
        evidence=[
            AttributionEvidence(
                source="registry_polling",
                confidence_score=0.0,
                raw_excerpt={"changed_fields": ["proxy_server"]},
                notes=[],
            ),
        ],
        attribution_notes=["trial"],
    )
    pipe = layered_to_heuristic_pipeline(layered)
    blob = heuristic_attribution_to_audit_dict(pipe)
    assert blob.get("candidate_actor") is not None
    assert isinstance(blob.get("evidence"), list)
    assert "evidence" in blob


def test_listener_parser_ports_plain_invokes(monkeypatch: pytest.MonkeyPatch) -> None:
    """Listener path calls ``attribution_payload`` when run is mocked to avoid netstat."""

    from src.proxy_guard import listener_attribution as la

    def fake_attrib_payload(port: int, *, run=None):
        _ = port, run
        return {"owners": [{"pid": 7, "process_name": "p.exe"}], "notes": []}

    monkeypatch.setattr(la, "attribution_payload", fake_attrib_payload)
    r = la.attribute_localhost_proxy_listener(
        "127.0.0.1:5000",
        run=lambda *_a, **_k: pytest.fail("unexpected subprocess invocation"),
    )
    assert r.attribution_confidence == "medium"
    assert r.candidate_actor is not None
    assert r.candidate_actor.pid == 7
