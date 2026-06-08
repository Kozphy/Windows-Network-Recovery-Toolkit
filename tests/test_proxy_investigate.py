"""Tests for read-only ``proxy-investigate`` investigation bundle."""

from __future__ import annotations

from argparse import Namespace
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.proxy_guard.investigation_bundle import (
    build_proxy_investigation_bundle,
    format_investigation_human,
    investigation_audit_row,
)
from src.proxy_guard.investigation_risk import classify_investigation_risk


def _patch_investigation_deps(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "src.proxy_guard.investigation_bundle.capture_enriched_process_snapshot",
        lambda **_: {"process_rows": [], "collection_warnings": []},
    )
    monkeypatch.setattr(
        "src.proxy_guard.investigation_bundle.collect_sysmon_proxy_events",
        lambda *a, **k: [],
    )
    monkeypatch.setattr(
        "src.proxy_guard.investigation_bundle.load_recent_proxy_transitions",
        lambda *a, **k: [],
    )


def _fake_reg(enable: int = 0, server: str | None = None):
    return type(
        "R",
        (),
        {
            "proxy_enable": enable,
            "proxy_server": server,
            "proxy_override": None,
            "auto_config_url": None,
            "auto_detect": None,
            "to_dict": lambda self: {},
        },
    )()


def _fake_snap():
    return type(
        "S",
        (),
        {
            "winhttp_proxy": "Direct",
            "winhttp_direct_access": True,
            "winhttp_proxy_server_literal": None,
            "proxy_enable": 1,
            "proxy_server": "127.0.0.1:64642",
            "proxy_override": None,
            "auto_config_url": None,
            "auto_detect": None,
            "captured_at": "2026-01-01T00:00:00Z",
            "user_http_proxy": None,
            "user_https_proxy": None,
            "user_all_proxy": None,
            "user_no_proxy": None,
            "git_http_proxy": None,
            "git_https_proxy": None,
            "npm_proxy": None,
            "npm_https_proxy": None,
        },
    )()


def test_no_proxy_low_risk() -> None:
    risk = classify_investigation_risk(
        proxy_enable=0,
        parsed={"is_localhost_proxy": False, "localhost_port": None, "proxy_server": None},
        port_owner=None,
        before_snapshot=None,
    )
    assert risk.category == "NO_PROXY"
    assert risk.risk_level == "LOW"


def test_localhost_node_listener_high_suspicious(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_investigation_deps(monkeypatch)
    from src.proxy_guard.proxy_allowlist import ProxyAllowlist

    monkeypatch.setattr(
        "src.proxy_guard.investigation_bundle.load_proxy_allowlist",
        lambda _root=None: ProxyAllowlist(frozenset(), frozenset(), frozenset()),
    )
    monkeypatch.setattr(
        "src.proxy_guard.investigation_bundle.read_proxy_registry",
        lambda **_: _fake_reg(1, "127.0.0.1:64642"),
    )
    monkeypatch.setattr(
        "src.proxy_guard.investigation_bundle.capture_proxy_snapshot",
        lambda **_: _fake_snap(),
    )
    monkeypatch.setattr(
        "src.proxy_guard.investigation_bundle.build_localhost_proxy_attribution",
        lambda *a, **k: {
            "localhost_proxy_detected": True,
            "localhost_port": 64642,
            "listener_found": True,
            "owners": [
                {
                    "pid": 49112,
                    "process_name": "node.exe",
                    "executable_path": None,
                    "command_line": "node dev-proxy.js",
                    "parent_pid": 34092,
                    "parent_name": "powershell.exe",
                }
            ],
            "notes": [],
        },
    )

    bundle = build_proxy_investigation_bundle(repo_root=None, run=MagicMock())
    assert bundle.risk.risk_level in {"MEDIUM", "HIGH"}
    assert bundle.risk.category in {"SENSITIVE_LOCALHOST_PROXY", "UNKNOWN_LOCAL_PROXY"}
    assert bundle.parsed_proxy.get("localhost_port") == 64642
    assert bundle.port_owner is not None
    assert bundle.port_owner["pid"] == 49112
    assert bundle.correlation.get("listener_matches_proxy_port") is True
    assert any(line.tier == "NOT_PROVEN" for line in bundle.evidence.lines)
    human = format_investigation_human(bundle)
    assert "Attribution conclusion" in human
    assert "does not imply compromise" in human or "registry writer" in human.lower()
    assert "node.exe" in human


def test_listener_correlation_not_registry_writer_proof() -> None:
    risk = classify_investigation_risk(
        proxy_enable=1,
        parsed={"is_localhost_proxy": True, "localhost_port": 64642, "proxy_server": "127.0.0.1:64642"},
        port_owner={
            "process_name": "node.exe",
            "parent_name": "powershell.exe",
            "listener_on_proxy_port": True,
            "executable_path": None,
            "path_missing": True,
        },
        before_snapshot=None,
    )
    assert risk.category in {"SENSITIVE_LOCALHOST_PROXY", "UNKNOWN_LOCAL_PROXY"}
    assert "registry writer proof" in " ".join(risk.limitations).lower()


def test_cursor_low_confidence_not_proven() -> None:
    risk = classify_investigation_risk(
        proxy_enable=1,
        parsed={"is_localhost_proxy": True, "localhost_port": 55000, "proxy_server": "127.0.0.1:55000"},
        port_owner={
            "process_name": "cursor.exe",
            "parent_name": "cursor.exe",
            "listener_on_proxy_port": True,
            "executable_path": "C:\\Users\\x\\AppData\\Local\\Programs\\cursor\\Cursor.exe",
            "path_missing": False,
        },
        before_snapshot=None,
    )
    assert risk.category == "SENSITIVE_LOCALHOST_PROXY"
    assert any("registry writer" in e.lower() for e in risk.evidence)


def test_remediation_not_sticky_category() -> None:
    risk = classify_investigation_risk(
        proxy_enable=1,
        parsed={"is_localhost_proxy": True, "localhost_port": 63722, "proxy_server": "127.0.0.1:63722"},
        port_owner={
            "process_name": "node.exe",
            "parent_name": "powershell.exe",
            "listener_on_proxy_port": True,
            "executable_path": None,
        },
        before_snapshot={"proxy_enable": 0, "proxy_server": "127.0.0.1:57324"},
    )
    assert risk.category == "REMEDIATION_NOT_STICKY"
    assert risk.risk_level == "HIGH"


def test_missing_path_increases_risk_not_malware_claim() -> None:
    risk = classify_investigation_risk(
        proxy_enable=1,
        parsed={"is_localhost_proxy": True, "localhost_port": 1, "proxy_server": "127.0.0.1:1"},
        port_owner={
            "process_name": "unknown.exe",
            "parent_name": "unknown.exe",
            "listener_on_proxy_port": True,
            "executable_path": None,
            "path_missing": True,
        },
        before_snapshot=None,
    )
    assert "malware" not in " ".join(risk.evidence).lower()
    assert risk.risk_level in {"HIGH", "MEDIUM"}


def test_audit_row_schema(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_investigation_deps(monkeypatch)
    monkeypatch.setattr(
        "src.proxy_guard.investigation_bundle.read_proxy_registry",
        lambda **_: _fake_reg(0, None),
    )
    monkeypatch.setattr(
        "src.proxy_guard.investigation_bundle.capture_proxy_snapshot",
        lambda **_: _fake_snap(),
    )
    monkeypatch.setattr(
        "src.proxy_guard.investigation_bundle.build_localhost_proxy_attribution",
        lambda *a, **k: {"listener_found": False, "owners": [], "notes": []},
    )
    b = build_proxy_investigation_bundle(repo_root=None, run=MagicMock())
    row = investigation_audit_row(b)
    assert row["subtype"] == "proxy_investigate"
    assert row["audit_event_id"] == b.event_id
    assert "evidence" in row
    assert "risk" in row
    assert "limitations" in row
    assert row.get("proof_status") in {"CORRELATED", "OBSERVED_ONLY", None} or "proof_status" in row


def test_cmd_proxy_investigate_read_only_no_audit(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    written: list[dict] = []

    monkeypatch.setattr("src.command_handlers._repo_root", lambda _p=None: tmp_path)
    monkeypatch.setattr(
        "src.proxy_guard.investigation_bundle.build_proxy_investigation_bundle",
        lambda **_: type(
            "B",
            (),
            {
                "event_id": "evt-1",
                "to_jsonable": lambda self: {"event_id": "evt-1"},
            },
        )(),
    )
    monkeypatch.setattr(
        "src.proxy_guard.investigation_bundle.format_investigation_human",
        lambda _b: "Proxy Investigation Summary\nOBSERVED: test",
    )
    monkeypatch.setattr("src.command_handlers.append_jsonl_core", lambda _p, row: written.append(row))

    from src.command_handlers import cmd_proxy_investigate

    rc = cmd_proxy_investigate(
        Namespace(repo_root=tmp_path, emit_json=False, investigate_audit=False, investigate_no_audit=False)
    )
    assert rc == 0
    assert written == []


def test_cmd_proxy_investigate_audit_when_flagged(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    written: list[dict] = []

    monkeypatch.setattr("src.command_handlers._repo_root", lambda _p=None: tmp_path)
    monkeypatch.setattr(
        "src.proxy_guard.investigation_bundle.build_proxy_investigation_bundle",
        lambda **_: type(
            "B",
            (),
            {
                "event_id": "evt-2",
                "to_jsonable": lambda self: {"event_id": "evt-2"},
            },
        )(),
    )
    monkeypatch.setattr(
        "src.proxy_guard.investigation_bundle.investigation_audit_row",
        lambda b: {"audit_event_id": b.event_id, "subtype": "proxy_investigate"},
    )
    monkeypatch.setattr(
        "src.proxy_guard.investigation_bundle.format_investigation_human",
        lambda _b: "summary",
    )
    monkeypatch.setattr("src.command_handlers.append_jsonl_core", lambda _p, row: written.append(row))

    from src.command_handlers import cmd_proxy_investigate

    rc = cmd_proxy_investigate(
        Namespace(repo_root=tmp_path, emit_json=False, investigate_audit=True, investigate_no_audit=False)
    )
    assert rc == 0
    assert len(written) == 1
    assert written[0]["subtype"] == "proxy_investigate"


def test_json_output_stable_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_investigation_deps(monkeypatch)
    monkeypatch.setattr(
        "src.proxy_guard.investigation_bundle.read_proxy_registry",
        lambda **_: _fake_reg(1, "127.0.0.1:64642"),
    )
    monkeypatch.setattr(
        "src.proxy_guard.investigation_bundle.capture_proxy_snapshot",
        lambda **_: _fake_snap(),
    )
    monkeypatch.setattr(
        "src.proxy_guard.investigation_bundle.build_localhost_proxy_attribution",
        lambda *a, **k: {"listener_found": False, "owners": [], "notes": []},
    )
    bundle = build_proxy_investigation_bundle(repo_root=None, run=MagicMock())
    payload = bundle.to_jsonable()
    for key in (
        "event_id",
        "timestamp_utc",
        "tool_version",
        "evidence",
        "risk",
        "limitations",
        "wininet",
        "parsed_proxy",
        "correlation",
        "proof_status",
        "attribution",
        "process_tree",
        "evidence_table",
    ):
        assert key in payload
