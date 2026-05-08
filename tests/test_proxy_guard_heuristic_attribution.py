"""Heuristic pipeline attribution (psutil-shaped snapshots, no live OS dependencies)."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from src.core.models import ProxyRegistrySnapshot
from src.proxy_guard.attribution import (
    attribute_proxy_change,
    heuristic_attribution_to_audit_dict,
    score_process,
)
from src.proxy_guard.control import run_proxy_guard_control
from src.proxy_guard.models import ProxySnapshot
from src.proxy_guard.policy import ProxyGuardPolicy


def test_attribute_returns_unavailable_when_psutil_missing_or_snapshot_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("src.proxy_guard.attribution.collect_process_snapshot", lambda: [])
    outcome = attribute_proxy_change()
    assert outcome.attribution_method == "unavailable"
    assert outcome.candidate_actor is None
    assert outcome.attribution_confidence == "unknown"

    empty = attribute_proxy_change(process_snapshot=[])
    assert empty.attribution_method == "unavailable"


def test_attribute_returns_unknown_when_no_suspicious_processes() -> None:
    snap = [
        {
            "pid": 100,
            "name": "notepad.exe",
            "exe": "C:\\Windows\\System32\\notepad.exe",
            "cmdline": "notepad.exe",
            "ppid": 50,
            "create_time": 1_710_000_000.0,
        },
    ]
    out = attribute_proxy_change(process_snapshot=snap, now=1_710_000_100.0)
    assert out.candidate_actor is None
    assert out.attribution_confidence == "unknown"
    assert out.attribution_method == "psutil_snapshot_heuristic"


def test_attribute_selects_proxy_tool_candidate() -> None:
    snap = [
        {
            "pid": 100,
            "name": "notepad.exe",
            "exe": "C:\\Windows\\System32\\notepad.exe",
            "cmdline": "notepad.exe",
            "ppid": 50,
            "create_time": 1_710_000_000.0,
        },
        {
            "pid": 8420,
            "name": "clash.exe",
            "exe": "C:\\Program Files\\Clash\\clash-v2ray-helper.exe",
            "cmdline": "clash.exe --proxy 127.0.0.1:7890",
            "ppid": 3000,
            "create_time": 1_710_000_020.0,
        },
    ]
    out = attribute_proxy_change(process_snapshot=snap, now=1_710_000_030.0, recent_window_seconds=30)
    assert out.candidate_actor is not None
    assert out.candidate_actor.process_name == "clash.exe"
    assert out.candidate_actor.score == 100
    reasons = set(out.candidate_actor.reasons)
    assert "matched_keyword:clash" in reasons
    assert "matched_keyword:proxy" in reasons
    assert "network_proxy_tool:clash" in reasons
    assert "network_proxy_tool:v2ray" in reasons


def test_attribute_scores_high_risk_proxy_tool_higher_than_generic_process() -> None:
    snap = [
        {
            "pid": 1,
            "name": "generic.exe",
            "exe": "C:\\generic.exe",
            "cmdline": "generic.exe harmless",
            "ppid": 0,
            "create_time": 1_710_000_000.0,
        },
        {
            "pid": 2,
            "name": "node.exe",
            "exe": "C:\\Prog\\node.exe",
            "cmdline": "node server.js",
            "ppid": 0,
            "create_time": 1_710_000_000.0,
        },
        {
            "pid": 9,
            "name": "clash_win.exe",
            "exe": "C:\\vpn\\clash_win.exe",
            "cmdline": "clash_win.exe",
            "ppid": 0,
            "create_time": 1_710_000_000.0,
        },
    ]
    ts = 1_710_090_000.0
    out = attribute_proxy_change(process_snapshot=snap, now=ts)
    assert out.candidate_actor is not None
    assert out.candidate_actor.pid == 9
    node_score = score_process(snap[1], now=ts, recent_window_seconds=30)[0]
    assert out.candidate_actor.score > node_score


def test_attribute_confidence_medium_for_score_80_or_more() -> None:
    snap = [
        {
            "pid": 8420,
            "name": "clash.exe",
            "exe": "C:\\Clash\\clash-v2ray-bundle.exe",
            "cmdline": "clash --proxy",
            "ppid": 1,
            "create_time": 1_710_000_020.0,
        },
    ]
    out = attribute_proxy_change(process_snapshot=snap, now=1_710_000_030.0)
    assert out.candidate_actor is not None
    assert out.candidate_actor.score >= 80
    assert out.attribution_confidence == "medium"


def test_attribute_confidence_low_for_score_40_to_79() -> None:
    snap = [
        {
            "pid": 7,
            "name": "dev.exe",
            "exe": "C:\\dev.exe",
            "cmdline": "python -m npm install",
            "ppid": 0,
            "create_time": 1_708_000_000.0,
        },
    ]
    out = attribute_proxy_change(process_snapshot=snap, now=1_710_090_000.0, recent_window_seconds=30)
    assert out.candidate_actor is not None
    assert 40 <= out.candidate_actor.score < 80
    assert out.attribution_confidence == "low"


def test_attribute_caps_score_at_100() -> None:
    noisy = (
        "clash v2ray shadowsocks fiddler charles vpn tunnel mitm proxy node npm python java "
        "electron cursor code"
    )
    snap = [{"pid": 1, "name": noisy[:40], "exe": noisy + "\\tool.exe", "cmdline": noisy, "ppid": 0}]
    sc, _ = score_process(snap[0], now=1_710_090_000.0, recent_window_seconds=900)
    assert sc == 100
    out = attribute_proxy_change(process_snapshot=snap, now=1_710_090_000.0, recent_window_seconds=900)
    assert out.candidate_actor is not None
    assert out.candidate_actor.score == 100


def test_attribute_failure_does_not_crash_proxy_guard(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    def boom(*_a: object, **_k: object) -> None:
        raise RuntimeError("simulated")

    monkeypatch.setattr("src.proxy_guard.guard.registry_layer_attribute_proxy_change", boom)

    off = ProxyRegistrySnapshot(
        proxy_enable=0,
        proxy_server=None,
        auto_config_url=None,
        auto_detect=0,
        proxy_override=None,
    )
    on = ProxyRegistrySnapshot(
        proxy_enable=1,
        proxy_server="127.0.0.1:65000",
        auto_config_url=None,
        auto_detect=0,
        proxy_override=None,
    )
    after = off

    def _full(reg: ProxyRegistrySnapshot) -> ProxySnapshot:
        return ProxySnapshot(
            proxy_enable=reg.proxy_enable,
            proxy_server=reg.proxy_server,
            proxy_override=None,
            auto_config_url=reg.auto_config_url,
            auto_detect=reg.auto_detect,
            winhttp_proxy="",
            winhttp_direct_access=True,
            winhttp_proxy_server_literal=None,
            git_http_proxy=None,
            git_https_proxy=None,
            npm_proxy=None,
            npm_https_proxy=None,
            user_http_proxy=None,
            user_https_proxy=None,
            user_all_proxy=None,
            user_no_proxy=None,
            captured_at="t",
        )

    lkg = _full(off)

    with (
        patch("src.proxy_guard.guard.read_proxy_registry_with_retries") as mock_read,
        patch("src.proxy_guard.guard.capture_proxy_snapshot", side_effect=lambda **kw: _full(kw["registry_snapshot"])),
        patch("src.proxy_guard.guard.load_lkg_snapshot", return_value=lkg),
        patch("src.proxy_guard.guard._safe_listen_attribution") as mock_safe,
        patch("src.proxy_guard.guard.execute_lkg_snapshot_rollback") as mock_rb,
    ):
        mock_read.side_effect = [(off, ()), (off, ()), (on, ()), (after, ())]
        mock_safe.return_value = (
            {"port": 65000, "owners": [{"process_name": "x.exe", "pid": 1}], "notes": []},
            (),
        )
        mock_rb.return_value = {
            "rollback_kind": "lkg_restore",
            "skipped": False,
            "success": True,
            "wininet_reg": [],
            "winhttp_restore": None,
        }
        policy = ProxyGuardPolicy(
            source_path=tmp_path / "p.json",
            allowed_process_name_substrings=(),
            allowed_process_names_exact=(),
            allow_when_attribution_empty=False,
        )
        log = tmp_path / "logs" / "guard.jsonl"
        run_proxy_guard_control(
            interval=0.01,
            once=False,
            auto_rollback=True,
            policy=policy,
            jsonl_path=log,
            dry_run_rollback=True,
            run=subprocess.run,
            exit_after_registry_change_events=1,
            repo_root=tmp_path,
        )


def test_proxy_change_audit_event_includes_attribute_object(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    captured: list[dict] = []

    fixed_pipeline = attribute_proxy_change(
        process_snapshot=[
            {
                "pid": 1,
                "name": "vpnagent.exe",
                "exe": "C:\\corp\\vpnagent.exe",
                "cmdline": "vpnagent",
                "ppid": 0,
            },
        ],
        now=1_710_090_000.0,
    )

    monkeypatch.setattr(
        "src.proxy_guard.guard.registry_layer_attribute_proxy_change",
        lambda *a, **k: None,
    )
    monkeypatch.setattr(
        "src.proxy_guard.guard.layered_to_heuristic_pipeline",
        lambda _layered: fixed_pipeline,
    )
    monkeypatch.setattr(
        "src.proxy_guard.guard.emit_pipeline_audit_v1",
        lambda repo, blob: captured.append(blob),
    )

    off = ProxyRegistrySnapshot(
        proxy_enable=0,
        proxy_server=None,
        auto_config_url=None,
        auto_detect=0,
        proxy_override=None,
    )
    on = ProxyRegistrySnapshot(
        proxy_enable=1,
        proxy_server="127.0.0.1:1",
        auto_config_url=None,
        auto_detect=0,
        proxy_override=None,
    )

    def _full(reg: ProxyRegistrySnapshot) -> ProxySnapshot:
        return ProxySnapshot(
            proxy_enable=reg.proxy_enable,
            proxy_server=reg.proxy_server,
            proxy_override=reg.proxy_override,
            auto_config_url=reg.auto_config_url,
            auto_detect=reg.auto_detect,
            winhttp_proxy="",
            winhttp_direct_access=True,
            winhttp_proxy_server_literal=None,
            git_http_proxy=None,
            git_https_proxy=None,
            npm_proxy=None,
            npm_https_proxy=None,
            user_http_proxy=None,
            user_https_proxy=None,
            user_all_proxy=None,
            user_no_proxy=None,
            captured_at="ts",
        )

    with (
        patch("src.proxy_guard.guard.read_proxy_registry_with_retries") as mock_read,
        patch("src.proxy_guard.guard.capture_proxy_snapshot", side_effect=lambda **kw: _full(kw["registry_snapshot"])),
        patch("src.proxy_guard.guard.load_lkg_snapshot") as mock_lkg,
        patch("src.proxy_guard.guard._safe_listen_attribution") as mock_safe,
        patch("src.proxy_guard.guard.execute_lkg_snapshot_rollback"),
    ):
        mock_read.side_effect = [(off, ()), (off, ()), (on, ())]
        mock_lkg.return_value = _full(off)
        mock_safe.return_value = (
            {"port": 1, "owners": [{"process_name": "vpnagent.exe", "pid": 1}], "notes": []},
            (),
        )
        policy = ProxyGuardPolicy(
            source_path=tmp_path / "p.json",
            allowed_process_name_substrings=(),
            allowed_process_names_exact=(),
            allow_when_attribution_empty=False,
        )
        run_proxy_guard_control(
            interval=0.01,
            once=False,
            auto_rollback=False,
            policy=policy,
            jsonl_path=tmp_path / "logs" / "c.jsonl",
            dry_run_rollback=True,
            run=subprocess.run,
            exit_after_registry_change_events=1,
            repo_root=tmp_path,
        )

    assert captured, "emit_pipeline_audit_v1 should have been called"
    attr = captured[0].get("attribute") or {}
    assert "attribution_confidence" in attr
    assert "attribution_method" in attr
    assert "attribution_notes" in attr
    assert "candidate_actor" in attr
    audit = heuristic_attribution_to_audit_dict(
        attribute_proxy_change(
            process_snapshot=[
                {"pid": 1, "name": "n.exe", "exe": "", "cmdline": "", "ppid": 0},
            ],
            now=1_710_090_000.0,
        ),
    )
    assert set(audit.keys()) >= {
        "candidate_actor",
        "attribution_confidence",
        "attribution_method",
        "attribution_notes",
    }