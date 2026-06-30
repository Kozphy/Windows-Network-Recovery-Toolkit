"""DEAD_PROXY_CONFIG workflow — schema, export, hints, read-only contracts."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from windows_network_toolkit.dead_proxy_incident import export_dead_proxy_incident_bundle
from windows_network_toolkit.proxy_diagnostic_hints import build_proxy_status_hints
from windows_network_toolkit.proxy_guardian import run_proxy_guardian_once
from windows_network_toolkit.proxy_health import ProxyStatus
from windows_network_toolkit.watch import run_proxy_watch
from windows_network_toolkit.watch_schema import (
    PROXY_WATCH_SCHEMA_VERSION,
    normalize_proxy_watch_event,
)


def test_normalize_proxy_watch_event_schema() -> None:
    event = {
        "event": "proxy_change",
        "old_state": {"wininet_proxy_enabled": 0},
        "new_state": {"wininet_proxy_enabled": 1, "wininet_proxy_server": "127.0.0.1:1"},
        "health_audit": {
            "classification": {"incident_class": "DEAD_PROXY_CONFIG"},
            "limitations": ["test limitation"],
        },
        "transition_evidence": {"proof_tier": "T2"},
    }
    normalized = normalize_proxy_watch_event(event)
    assert normalized["schema_version"] == PROXY_WATCH_SCHEMA_VERSION
    assert normalized["before_state"]["wininet_proxy_enabled"] == 0
    assert normalized["after_state"]["wininet_proxy_enabled"] == 1
    assert normalized["proof_tier"] == "T2"
    assert "test limitation" in normalized["limitations"]


def test_proxy_watch_dead_proxy_fixture_emits_schema_fields() -> None:
    sequence = [
        {
            "wininet_proxy_enabled": False,
            "wininet_proxy_server": "",
            "wininet_auto_config_url": "",
            "winhttp_direct_access": True,
            "localhost_port": None,
        },
        {
            "wininet_proxy_enabled": True,
            "wininet_proxy_server": "127.0.0.1:62285",
            "wininet_auto_config_url": "",
            "winhttp_direct_access": True,
            "localhost_port": 62285,
        },
    ]
    health_inject = {
        "host": "127.0.0.1",
        "port": 62285,
        "timestamp_utc": "2026-06-12T00:00:00Z",
        "tcp_listening": False,
        "tcp_connect_ok": False,
        "proxy_https_connect_ok": False,
        "direct_probe_ok": True,
        "external_probe_ok": False,
        "proxy_status": ProxyStatus.DEAD_LOCALHOST_PROXY.value,
        "evidence": ["no listener"],
        "limitations": ["fixture"],
    }
    payload = run_proxy_watch(
        inject_sequence=sequence,
        health_inject=health_inject,
        run_direct_probe=False,
        run_proxy_probe=False,
    )
    changes = [e for e in payload["events"] if e.get("event") == "proxy_change"]
    assert len(changes) == 1
    change = changes[0]
    assert change["schema_version"] == PROXY_WATCH_SCHEMA_VERSION
    assert change["classification"]["incident_class"] == "DEAD_PROXY_CONFIG"
    assert change["proof_tier"]


def test_proxy_watch_read_only_never_calls_proxy_disable() -> None:
    sequence = [
        {
            "wininet_proxy_enabled": True,
            "wininet_proxy_server": "127.0.0.1:62285",
            "wininet_auto_config_url": "",
            "winhttp_direct_access": True,
            "localhost_port": 62285,
        },
    ]
    with patch("windows_network_toolkit.proxy_remediation.run_proxy_disable") as disable:
        run_proxy_watch(inject_sequence=sequence, run_direct_probe=False, run_proxy_probe=False)
    disable.assert_not_called()


def test_build_proxy_status_hints_no_proxy() -> None:
    hints = build_proxy_status_hints(
        classification="NO_PROXY",
        payload={"wininet": {"ProxyEnable": 0}, "winhttp": {"direct_access": True}},
        direct_probe_ok=False,
    )
    blob = " ".join(hints).lower()
    assert "direct https probe failed" in blob
    assert "ssh" in blob


def test_export_dead_proxy_incident_bundle(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    audit = tmp_path / ".audit"
    audit.mkdir()
    (audit / "proxy-watch.jsonl").write_text('{"event":"poll"}\n', encoding="utf-8")

    status = {
        "classification": "DEAD_PROXY_CONFIG",
        "timestamp_utc": "2026-01-01T00:00:00Z",
        "wininet": {"ProxyEnable": 1, "ProxyServer": "127.0.0.1:1"},
        "winhttp": {"direct_access": True},
    }
    health = {"event": "proxy_health_check", "classification": {"incident_class": "DEAD_PROXY_CONFIG"}}
    state = {
        "wininet_proxy_enabled": True,
        "wininet_proxy_server": "127.0.0.1:1",
        "winhttp_direct_access": True,
    }

    monkeypatch.setattr(
        "windows_network_toolkit.dead_proxy_incident.run_proxy_status",
        lambda **_: status,
    )
    monkeypatch.setattr(
        "windows_network_toolkit.dead_proxy_incident.collect_proxy_state_model",
        lambda **_: type("M", (), {"to_dict": lambda self: state})(),
    )
    monkeypatch.setattr(
        "windows_network_toolkit.dead_proxy_incident.run_proxy_health_for_state",
        lambda *a, **k: health,
    )

    out = tmp_path / "reports" / "bundle"
    payload = export_dead_proxy_incident_bundle(repo_root=tmp_path, audit_dir=audit, out_dir=out)
    assert payload["classification"] == "DEAD_PROXY_CONFIG"
    assert (out / "proxy-status.json").is_file()
    assert (out / "proxy-health.json").is_file()
    assert (out / "proxy-watch.jsonl").is_file()
    assert json.loads((out / "proxy-status.json").read_text(encoding="utf-8"))["classification"] == "DEAD_PROXY_CONFIG"


def test_guardian_gate_reason_when_not_dead() -> None:
    with patch(
        "windows_network_toolkit.proxy_guardian.run_proxy_status",
        return_value={"classification": "NO_PROXY", "timestamp_utc": "t"},
    ):
        out = run_proxy_guardian_once(dry_run=False)
    assert out["gate_reason"] == "classification_not_dead_proxy"
    assert out["operator_next_steps"]


def test_proxy_status_60505_fixture_cli(capsys) -> None:
    from windows_network_toolkit import cli

    rc = cli.main(["proxy-status", "--fixture", "dead_proxy_60505.json"])
    payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert payload["classification"] == "DEAD_PROXY_CONFIG"
    assert payload["localhost_port"] == 60505
    assert payload["wininet"]["ProxyServer"] == "127.0.0.1:60505"
    assert payload["winhttp"]["direct_access"] is True
    hints = " ".join(payload.get("diagnostic_hints") or []).lower()
    assert "proxy-health" in hints or "preview" in hints
    assert "malware" not in hints


def test_proxy_health_60505_before_proxy_path_fails() -> None:
    from pathlib import Path

    fixture = Path(__file__).resolve().parents[1] / "fixtures" / "enert" / "dead_proxy_60505.json"
    data = json.loads(fixture.read_text(encoding="utf-8"))
    inject = data["health_inject"]

    from windows_network_toolkit.proxy_health import (
        check_localhost_proxy_health,
        classify_incident_from_health,
    )

    health = check_localhost_proxy_health(
        "127.0.0.1",
        60505,
        inject=inject,
        run_direct_probe=False,
        run_proxy_probe=False,
    )
    assert health.direct_probe_ok is True
    assert health.proxy_https_connect_ok is False
    assert health.tcp_listening is False
    cls = classify_incident_from_health(health, wininet_enabled=True)
    assert cls["incident_class"] == "DEAD_PROXY_CONFIG"


def test_proxy_health_60505_after_disable_direct_ok() -> None:
    from pathlib import Path

    from windows_network_toolkit.proxy_health import (
        check_localhost_proxy_health,
        classify_incident_from_health,
    )

    fixture = Path(__file__).resolve().parents[1] / "fixtures" / "enert" / "dead_proxy_60505.json"
    data = json.loads(fixture.read_text(encoding="utf-8"))
    inject = data["health_inject_after_disable"]

    health = check_localhost_proxy_health(
        "127.0.0.1",
        60505,
        inject=inject,
        run_direct_probe=False,
        run_proxy_probe=False,
    )
    assert health.direct_probe_ok is True
    cls = classify_incident_from_health(health, wininet_enabled=False)
    assert cls["incident_class"] in {"NO_PROXY_DIRECT_OK", "DIRECT_CONNECTIVITY_ISSUE", "INSUFFICIENT_DATA"}


def test_proxy_health_60505_fixture_cli_json(capsys) -> None:
    from windows_network_toolkit import cli

    rc = cli.main(
        [
            "proxy-health",
            "--fixture",
            "tests/fixtures/enert/dead_proxy_60505.json",
            "--json",
            "--no-direct-probe",
            "--no-proxy-probe",
        ]
    )
    payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert payload["classification"]["incident_class"] == "DEAD_PROXY_CONFIG"
    assert payload["health"]["direct_probe_ok"] is True
    assert payload["health"]["proxy_https_connect_ok"] is False


def test_diagnose_proof_60505_ssh_not_proxy_claim(capsys) -> None:
    from windows_network_toolkit import cli

    rc = cli.main(["diagnose", "--proof", "--fixture", "dead_proxy_60505.json"])
    payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    blob = json.dumps(payload).lower()
    assert "publickey" in blob or "ssh" in blob
    assert "malware" not in blob or "does not prove" in blob


def test_proxy_disable_dry_run_default_no_mutation() -> None:
    with patch("windows_network_toolkit.proxy_remediation.apply_mutations") as mutate:
        from windows_network_toolkit.proxy_remediation import run_proxy_disable

        result = run_proxy_disable(dry_run=True, confirm="")
    mutate.assert_not_called()
    assert result.get("dry_run") is True or result.get("unsupported_platform") is True
    if result.get("dry_run"):
        assert result.get("action_allowed") is False
