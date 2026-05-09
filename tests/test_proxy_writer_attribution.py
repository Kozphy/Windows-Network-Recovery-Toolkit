"""Proxy writer attribution proof-boundary tests."""

from __future__ import annotations

import json
from pathlib import Path

from evidence.registry_writer import parse_procmon_csv, parse_security_4657_rows, parse_sysmon_event_rows
from proxy_guard.attribution import build_proxy_attribution_event
from proxy_guard.watch_registry import append_proxy_writer_event, import_procmon_trace


def _before() -> dict[str, object]:
    return {
        "ProxyEnable": 0,
        "ProxyServer": None,
        "AutoConfigURL": None,
        "ProxyOverride": None,
        "AutoDetect": 0,
    }


def _after() -> dict[str, object]:
    return {
        "ProxyEnable": 1,
        "ProxyServer": "127.0.0.1:8888",
        "AutoConfigURL": None,
        "ProxyOverride": None,
        "AutoDetect": 0,
    }


def test_proxy_change_without_writer_telemetry_is_not_proof() -> None:
    event = build_proxy_attribution_event(
        proxy_before=_before(),
        proxy_after=_after(),
        candidate_listeners=[],
        registry_writer_evidence=[],
        persistence_indicators={},
        certificate_indicators={},
        connectivity_before_after={},
    )

    assert event.evidence_level == "STATE_CHANGE"
    assert event.classification == "PROXY_CHANGED_WITH_NO_WRITER_PROOF"
    assert event.policy_gate["mode"] == "PREVIEW"
    assert any("writer proof unavailable" in item for item in event.limitations)
    assert event.registry_writer_evidence == []


def test_listener_process_on_proxy_port_is_candidate_actor_only() -> None:
    event = build_proxy_attribution_event(
        proxy_before=_before(),
        proxy_after=_after(),
        candidate_listeners=[
            {
                "role": "candidate_actor",
                "basis": "tcp_listener_on_configured_proxy_port",
                "pid": 4242,
                "process_name": "node.exe",
                "port": 8888,
            }
        ],
        registry_writer_evidence=[],
        persistence_indicators={},
        certificate_indicators={},
        connectivity_before_after={},
    )

    assert event.evidence_level == "CORRELATED_PROCESS"
    assert event.candidate_listeners[0]["role"] == "candidate_actor"
    assert event.registry_writer_evidence == []
    assert "writer" not in event.candidate_listeners[0]["role"]
    assert any("candidate_actor only" in item for item in event.limitations)


def test_sysmon_event_13_proxy_write_upgrades_to_writer_proof() -> None:
    evidence = parse_sysmon_event_rows(
        [
            {
                "EventID": 13,
                "UtcTime": "2026-05-09T01:02:03Z",
                "Image": r"C:\Tools\Fiddler\Fiddler.exe",
                "ProcessId": "1234",
                "User": r"DESKTOP\alice",
                "TargetObject": r"HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings\ProxyServer",
                "Details": "127.0.0.1:8888",
            }
        ]
    )

    event = build_proxy_attribution_event(
        proxy_before=_before(),
        proxy_after=_after(),
        registry_writer_evidence=evidence,
        persistence_indicators={},
        certificate_indicators={},
        connectivity_before_after={},
    )

    assert event.evidence_level == "WRITER_PROOF"
    assert event.classification == "KNOWN_DEV_PROXY"
    assert event.registry_writer_evidence[0]["event_source"] == "sysmon_event_13"
    assert event.registry_writer_evidence[0]["process_id"] == 1234


def test_security_event_4657_proxy_write_is_writer_proof_when_auditing_exists() -> None:
    evidence = parse_security_4657_rows(
        [
            {
                "EventID": 4657,
                "TimeCreated": "2026-05-09T01:02:03Z",
                "ProcessName": r"C:\Program Files\ExampleVPN\vpnclient.exe",
                "ProcessId": "55",
                "SubjectUserName": "alice",
                "ObjectName": r"\REGISTRY\USER\S-1-5-21\Software\Microsoft\Windows\CurrentVersion\Internet Settings",
                "ObjectValueName": "ProxyServer",
                "NewValue": "127.0.0.1:8888",
            }
        ]
    )

    event = build_proxy_attribution_event(
        proxy_before=_before(),
        proxy_after=_after(),
        registry_writer_evidence=evidence,
        persistence_indicators={},
        certificate_indicators={},
        connectivity_before_after={},
    )

    assert event.evidence_level == "WRITER_PROOF"
    assert event.classification == "KNOWN_VPN_OR_SECURITY_TOOL"
    assert event.registry_writer_evidence[0]["event_source"] == "windows_security_event_4657"


def test_unknown_writer_preview_without_risky_side_signals() -> None:
    evidence = parse_sysmon_event_rows(
        [
            {
                "EventID": 13,
                "Image": r"C:\Users\alice\AppData\Roaming\weird.exe",
                "TargetObject": r"HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings\ProxyEnable",
                "Details": "DWORD (0x00000001)",
            }
        ]
    )
    event = build_proxy_attribution_event(
        proxy_before=_before(),
        proxy_after=_after(),
        registry_writer_evidence=evidence,
        persistence_indicators={},
        certificate_indicators={},
        connectivity_before_after={},
    )

    assert event.evidence_level == "WRITER_PROOF"
    assert event.classification == "UNKNOWN_PROCESS_CHANGED_PROXY"
    assert event.policy_gate["mode"] == "PREVIEW"
    assert event.policy_gate["auto_remediation_allowed"] is False


def test_unknown_writer_with_localhost_proxy_and_cert_risk_blocks_auto_remediation() -> None:
    evidence = parse_sysmon_event_rows(
        [
            {
                "EventID": 13,
                "Image": r"C:\Users\alice\AppData\Roaming\weird.exe",
                "TargetObject": r"HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings\ProxyServer",
                "Details": "127.0.0.1:8888",
            }
        ]
    )
    event = build_proxy_attribution_event(
        proxy_before=_before(),
        proxy_after=_after(),
        registry_writer_evidence=evidence,
        persistence_indicators={},
        certificate_indicators={"suspicious_certificates": [{"Subject": "CN=Local MITM Root"}]},
        connectivity_before_after={},
    )

    assert event.classification == "POSSIBLE_MITM_RISK"
    assert event.policy_gate["mode"] == "BLOCK"
    assert event.policy_gate["auto_remediation_allowed"] is False


def test_all_writer_events_are_append_only_jsonl(tmp_path: Path) -> None:
    path = tmp_path / "proxy_writer_audit.jsonl"
    first = build_proxy_attribution_event(
        proxy_before=_before(),
        proxy_after=_after(),
        registry_writer_evidence=[],
        persistence_indicators={},
        certificate_indicators={},
        connectivity_before_after={},
        event_id="evt-1",
    )
    second = build_proxy_attribution_event(
        proxy_before=_after(),
        proxy_after=_before(),
        registry_writer_evidence=[],
        persistence_indicators={},
        certificate_indicators={},
        connectivity_before_after={},
        event_id="evt-2",
    )

    append_proxy_writer_event(first, audit_path=path)
    append_proxy_writer_event(second, audit_path=path)

    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert [json.loads(line)["event_id"] for line in lines] == ["evt-1", "evt-2"]


def test_no_destructive_remediation_is_allowed_by_default() -> None:
    event = build_proxy_attribution_event(
        proxy_before=_before(),
        proxy_after=_after(),
        registry_writer_evidence=[],
        persistence_indicators={},
        certificate_indicators={},
        connectivity_before_after={},
    )
    controls = event.policy_gate["safety_controls"]

    assert event.policy_gate["auto_remediation_allowed"] is False
    assert controls["never_kill_process"] is True
    assert controls["never_delete_certificates"] is True
    assert controls["never_reset_firewall"] is True
    assert controls["never_disable_adapter"] is True
    assert event.policy_gate["registry_restore_requires_explicit_confirmation"] is True


def test_procmon_import_parses_proxy_regsetvalue_and_appends_audit(tmp_path: Path) -> None:
    csv_path = tmp_path / "procmon.csv"
    csv_path.write_text(
        "Time of Day,Process Name,PID,Operation,Path,Result,Detail\n"
        r"12:00:00.000,svc.exe,777,RegSetValue,HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings\ProxyServer,SUCCESS,127.0.0.1:8888"
        "\n",
        encoding="utf-8",
    )
    parsed = parse_procmon_csv(csv_path)
    assert len(parsed) == 1
    assert parsed[0].event_source == "procmon_csv"

    audit = tmp_path / "audit.jsonl"
    payload = import_procmon_trace(csv_path, audit_path=audit)
    assert payload["evidence_count"] == 1
    assert len(audit.read_text(encoding="utf-8").splitlines()) == 1
