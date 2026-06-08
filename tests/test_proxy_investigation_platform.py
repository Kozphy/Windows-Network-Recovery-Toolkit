"""Tests for endpoint proxy investigation platform upgrades."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.proxy_guard.attribution_levels import compute_attribution_level
from src.proxy_guard.attribution_model import AttributionEvidence
from src.proxy_guard.investigation_bundle import (
    build_proxy_investigation_bundle,
    format_investigation_human,
)
from src.proxy_guard.investigation_models import AttributionLevel
from src.proxy_guard.investigation_risk import classify_investigation_risk
from src.proxy_guard.parser import parse_proxy_server
from src.proxy_guard.process_tree import render_process_tree_json, render_process_tree_text
from src.proxy_guard.proxy_allowlist import ProxyAllowlist, allowlist_match_summary
from src.proxy_guard.proxy_transitions import (
    build_recovery_guidance,
    parse_since_duration,
    summarize_transition_row,
)
from src.proxy_guard.sysmon_attribution import attribution_evidence_from_sysmon_message, parse_sysmon_e13_message


def test_parse_localhost_proxy_port() -> None:
    parsed = parse_proxy_server("127.0.0.1:64394")
    assert parsed.is_localhost_proxy is True
    assert parsed.localhost_port == 64394


def test_process_tree_renderers() -> None:
    nodes = [
        {"process_name": "Cursor.exe", "pid": 1},
        {"process_name": "powershell.exe", "pid": 2},
        {"process_name": "node.exe", "pid": 3, "listens_on_localhost_port": 64394},
    ]
    text = render_process_tree_text(nodes, matched_port=64394)
    assert "Cursor.exe" in text
    assert "node.exe" in text
    assert "64394" in text
    payload = render_process_tree_json(nodes, matched_port=64394)
    assert payload["root"]["process_name"] == "Cursor.exe"
    assert payload["matched_localhost_port"] == 64394


def test_attribution_correlated_vs_strong() -> None:
    owner = {
        "pid": 99,
        "process_name": "node.exe",
        "command_line": "node --proxy localhost devserver",
        "listener_on_proxy_port": True,
    }
    rows = [
        {"pid": 99, "process_name": "node.exe", "parent_pid": 88, "command_line": owner["command_line"]},
        {"pid": 88, "process_name": "powershell.exe", "parent_pid": 77},
        {"pid": 77, "process_name": "Cursor.exe", "parent_pid": 4},
    ]
    conclusion = compute_attribution_level(
        owner=owner,
        process_rows=rows,
        sysmon_events=[],
        procmon_events=[],
        matched_port=64394,
        allowlist=ProxyAllowlist.defaults(),
    )
    assert conclusion.level == AttributionLevel.STRONG_CORRELATION
    assert "powershell.exe" in conclusion.parent_chain


def test_attribution_proven_via_sysmon_message() -> None:
    message = (
        "RuleName: -\n"
        "UtcTime: 2026-01-01 12:00:00.000\n"
        "ProcessGuid: {abc}\n"
        "ProcessId: 4242\n"
        "Image: C:\\Tools\\node.exe\n"
        "User: DESKTOP\\User\n"
        "TargetObject: HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Internet Settings\\ProxyEnable\n"
        "Details: DWORD (0x00000001)\n"
    )
    fields = parse_sysmon_e13_message(message)
    assert fields.get("processid") == "4242"
    ev = attribution_evidence_from_sysmon_message(message)
    assert ev is not None
    conclusion = compute_attribution_level(
        owner={"pid": 4242, "process_name": "node.exe", "listener_on_proxy_port": True},
        process_rows=[],
        sysmon_events=[ev],
        procmon_events=[],
        matched_port=8080,
        allowlist=ProxyAllowlist.defaults(),
    )
    assert conclusion.level == AttributionLevel.PROVEN_REGISTRY_WRITER


def test_procmon_csv_proof(tmp_path: Path) -> None:
    csv_text = (
        "Time of Day,Process Name,PID,Operation,Path,Result,Detail\n"
        "12:00:01.000,node.exe,4242,RegSetValue,"
        "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Internet Settings\\ProxyServer,"
        "SUCCESS,127.0.0.1:8080\n"
    )
    path = tmp_path / "procmon.csv"
    path.write_text(csv_text, encoding="utf-8")
    from src.proxy_guard.procmon_import import load_procmon_proxy_events

    events = load_procmon_proxy_events(str(path))
    assert events
    assert events[0].source == "procmon_csv"
    conclusion = compute_attribution_level(
        owner={"pid": 4242, "process_name": "node.exe", "listener_on_proxy_port": True},
        process_rows=[],
        sysmon_events=[],
        procmon_events=events,
        matched_port=8080,
        allowlist=ProxyAllowlist.defaults(),
    )
    assert conclusion.level == AttributionLevel.PROVEN_REGISTRY_WRITER


def test_allowlist_downgrades_risk() -> None:
    match = allowlist_match_summary(
        process_name="node.exe",
        executable_path=r"C:\Program Files\nodejs\node.exe",
        command_line="node mcp devserver localhost",
        allowlist=ProxyAllowlist(
            trusted_processes=frozenset({"node.exe"}),
            trusted_paths=frozenset(),
            trusted_commandline_keywords=frozenset({"mcp", "localhost"}),
        ),
    )
    assert match["any_match"] is True
    risk = classify_investigation_risk(
        proxy_enable=1,
        parsed={"is_localhost_proxy": True, "localhost_port": 8080, "proxy_server": "127.0.0.1:8080"},
        port_owner={
            "process_name": "node.exe",
            "listener_on_proxy_port": True,
            "executable_path": r"C:\Program Files\nodejs\node.exe",
        },
        before_snapshot=None,
        allowlist_match=True,
    )
    assert risk.risk_level == "LOW"
    assert risk.category == "TRUSTED_ALLOWLIST_MATCH"


def test_parse_since_duration() -> None:
    assert parse_since_duration("30m") == 1800
    assert parse_since_duration("2h") == 7200
    assert parse_since_duration("3600") == 3600


def _bundle_patches(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_reg = type(
        "R",
        (),
        {
            "proxy_enable": 1,
            "proxy_server": "127.0.0.1:64394",
            "proxy_override": None,
            "auto_config_url": None,
            "auto_detect": None,
            "to_dict": lambda self: {},
        },
    )()
    fake_snap = type(
        "S",
        (),
        {
            "winhttp_proxy": "Direct",
            "winhttp_direct_access": True,
            "winhttp_proxy_server_literal": None,
            "proxy_enable": 1,
            "proxy_server": "127.0.0.1:64394",
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
    monkeypatch.setattr(
        "src.proxy_guard.investigation_bundle.read_proxy_registry",
        lambda **_: fake_reg,
    )
    monkeypatch.setattr(
        "src.proxy_guard.investigation_bundle.capture_proxy_snapshot",
        lambda **_: fake_snap,
    )
    monkeypatch.setattr(
        "src.proxy_guard.investigation_bundle.build_localhost_proxy_attribution",
        lambda *a, **k: {
            "localhost_proxy_detected": True,
            "localhost_port": 64394,
            "listener_found": True,
            "owners": [
                {
                    "pid": 4242,
                    "process_name": "node.exe",
                    "executable_path": None,
                    "command_line": "node proxy devserver",
                    "parent_pid": 100,
                    "parent_name": "powershell.exe",
                }
            ],
            "notes": [],
        },
    )
    monkeypatch.setattr(
        "src.proxy_guard.investigation_bundle.capture_enriched_process_snapshot",
        lambda **_: {
            "process_rows": [
                {
                    "pid": 4242,
                    "process_name": "node.exe",
                    "parent_pid": 100,
                    "parent_process_name": "powershell.exe",
                    "path_status": "unresolved_path",
                },
                {"pid": 100, "process_name": "powershell.exe", "parent_pid": 50},
                {"pid": 50, "process_name": "Cursor.exe", "parent_pid": 4},
            ],
            "collection_warnings": [],
        },
    )
    monkeypatch.setattr(
        "src.proxy_guard.investigation_bundle.collect_sysmon_proxy_events",
        lambda *a, **k: [
            AttributionEvidence(
                source="unknown",
                confidence_score=0.0,
                notes=["Sysmon unavailable: registry writer cannot be proven."],
            )
        ],
    )
    monkeypatch.setattr(
        "src.proxy_guard.investigation_bundle.load_recent_proxy_transitions",
        lambda *a, **k: [],
    )


def test_build_recovery_guidance_no_proxy_with_history() -> None:
    interpretation, steps = build_recovery_guidance(
        proxy_enable=0,
        is_localhost_proxy=False,
        recent_transitions=[{"diff": {"before": {"proxy_enable": 1}, "after": {"proxy_enable": 0}}}],
        port_owner=None,
    )
    assert "currently disabled" in interpretation.lower()
    assert any("diagnose-live" in s for s in steps)
    assert not any("STOP_PROXY_LISTENER" in s for s in steps)


def test_summarize_transition_row() -> None:
    row = {
        "diff": {
            "before": {"proxy_enable": 0, "proxy_server": None},
            "after": {"proxy_enable": 1, "proxy_server": "127.0.0.1:8080"},
            "reason": "ProxyEnable enabled with localhost server",
        }
    }
    assert "ProxyEnable" in summarize_transition_row(row) or "localhost" in summarize_transition_row(row).lower()


def test_report_generation_sections(monkeypatch: pytest.MonkeyPatch) -> None:
    _bundle_patches(monkeypatch)
    bundle = build_proxy_investigation_bundle(repo_root=Path("."), run=MagicMock(), since_seconds="30m")
    human = format_investigation_human(bundle)
    for section in (
        "Current proxy state",
        "Situation",
        "Recent proxy transitions",
        "Candidate processes",
        "Process tree",
        "Evidence table",
        "Attribution conclusion",
        "Policy recommendation",
        "Limitations",
    ):
        assert section in human
    payload = bundle.to_jsonable()
    assert payload["attribution"]["level"] in {
        "CORRELATED",
        "STRONG_CORRELATION",
        "CANDIDATE",
    }
    assert "Sysmon unavailable" in " ".join(payload["limitations"]) or any(
        "Sysmon" in lim for lim in payload["limitations"]
    )
