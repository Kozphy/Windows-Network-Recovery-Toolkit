"""Network State Manager — pure logic and I/O with fakes (no live registry or elevation)."""

from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.cli import main as cli_main
from src.network_state import cli_handlers as ns_cli
from src.network_state.audit import append_restore_audit
from src.network_state.diff_engine import detect_suspicious_cases, drift_bundle
from src.network_state.events import emit_network_state_event
from src.network_state.evidence_import import parse_procmon_like_csv
from src.network_state.policy import NetworkStatePolicy, evaluate_network_state_policy
from src.network_state.report import build_network_state_report
from src.network_state.snapshot_store import append_snapshot, get_latest_named, list_profile_summaries, write_default_profile
from src.proxy_guard.models import ProxySnapshot
from src.proxy_guard.parser import parse_proxy_server


def _snap(**kw: object) -> ProxySnapshot:
    base = {
        "proxy_enable": 0,
        "proxy_server": None,
        "proxy_override": None,
        "auto_config_url": None,
        "auto_detect": None,
        "winhttp_proxy": "",
        "winhttp_direct_access": True,
        "winhttp_proxy_server_literal": None,
        "git_http_proxy": None,
        "git_https_proxy": None,
        "npm_proxy": None,
        "npm_https_proxy": None,
        "user_http_proxy": None,
        "user_https_proxy": None,
        "user_all_proxy": None,
        "user_no_proxy": None,
        "captured_at": "2024-01-01T00:00:00Z",
    }
    base.update(kw)
    return ProxySnapshot.from_json_dict(base)


def test_snapshot_append_list_roundtrip(tmp_path: Path) -> None:
    s = _snap(proxy_enable=0)
    row = append_snapshot(tmp_path, name="home-clean", snapshot=s)
    assert row["name"] == "home-clean"
    assert get_latest_named(tmp_path, "home-clean") is not None
    summaries = list_profile_summaries(tmp_path)
    assert len(summaries) == 1
    assert summaries[0]["name"] == "home-clean"


def test_set_default_writes_config(tmp_path: Path) -> None:
    append_snapshot(tmp_path, name="vpn-work", snapshot=_snap())
    path = write_default_profile(tmp_path, name="vpn-work")
    assert path.is_file()
    blob = json.loads(path.read_text(encoding="utf-8"))
    assert blob.get("name") == "vpn-work"


def test_diff_suspicious_loopback_and_policy() -> None:
    saved = _snap(proxy_enable=0, proxy_server=None)
    cur = _snap(proxy_enable=1, proxy_server="127.0.0.1:9999")
    bundle = drift_bundle(
        saved,
        cur,
        policy=NetworkStatePolicy.default(),
        attribution_heuristic={"owners": [{"process_name": "charles.exe"}]},
    )
    assert "proxy_enable" in (bundle.get("changed_fields") or {})
    assert "proxy_server_loopback_port_pattern" in bundle["suspicious_cases"]
    assert bundle.get("policy") is not None


def test_detect_suspicious_proxy_enable_and_pac() -> None:
    saved = _snap(proxy_enable=0, auto_config_url=None)
    cur = _snap(proxy_enable=1, auto_config_url="http://proxy/pac.js")
    flags = detect_suspicious_cases(saved, cur, {})
    assert "proxy_enable_escalated_off_to_on" in flags
    assert "auto_config_url_newly_set" in flags


def test_policy_blocked_host() -> None:
    pol = NetworkStatePolicy(
        allowed_process_names=(),
        blocked_process_names=(),
        allowed_proxy_hosts=(),
        blocked_proxy_hosts=("evil.proxy",),
        rollback_on_unknown_loopback=False,
        alert_on_unknown_loopback=False,
    )
    parsed = parse_proxy_server("evil.proxy:8080")
    out = evaluate_network_state_policy(pol, parsed=parsed, suspicions=[], attribution=None)
    assert out["decision"] == "blocked"


def test_policy_allowed_process_lowers_block_stress() -> None:
    pol = NetworkStatePolicy(
        allowed_process_names=("charles.exe",),
        blocked_process_names=(),
        allowed_proxy_hosts=(),
        blocked_proxy_hosts=(),
        rollback_on_unknown_loopback=False,
        alert_on_unknown_loopback=True,
    )
    parsed = parse_proxy_server("127.0.0.1:8888")
    out = evaluate_network_state_policy(
        pol,
        parsed=parsed,
        suspicions=["proxy_server_loopback_port_pattern"],
        attribution={"owners": [{"process_name": "Charles.exe"}]},
    )
    assert any(str(r).startswith("allowed_process_heuristic:") for r in out["reasons"])


def test_restore_audit_jsonl_two_phases(tmp_path: Path) -> None:
    append_restore_audit(
        tmp_path,
        phase="restore_pre_change",
        name="x",
        dry_run=True,
        preview_or_result={"dry": True},
    )
    append_restore_audit(
        tmp_path,
        phase="restore_post_change",
        name="x",
        dry_run=True,
        preview_or_result={"dry": True},
    )
    lines = (tmp_path / "logs" / "network_state_audit.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2


def test_events_emit_append(tmp_path: Path) -> None:
    emit_network_state_event(tmp_path, "report_generated", {"since": "1h"})
    p = tmp_path / "logs" / "network_state_events.jsonl"
    assert p.is_file()
    row = json.loads(p.read_text(encoding="utf-8").strip())
    assert row["event_type"] == "report_generated"


def test_report_generation_monkeypatch_capture(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cfg = tmp_path / "config"
    cfg.mkdir(parents=True)
    append_snapshot(tmp_path, name="base", snapshot=_snap())
    write_default_profile(tmp_path, name="base")
    emit_network_state_event(tmp_path, "drift_detected", {"suspicious_cases": ["proxy_server_loopback_port_pattern"]})

    import src.network_state.report as ns_report

    monkeypatch.setattr(ns_report, "capture_proxy_snapshot", lambda **_: _snap(proxy_enable=1))

    rep = build_network_state_report(tmp_path, since="24h", run=MagicMock())
    assert rep["default_profile_name"] == "base"
    assert rep["drift_vs_default"] == "drifted"


def test_restore_handler_preview_runs_known_good_twice_dry(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    append_snapshot(tmp_path, name="p", snapshot=_snap())
    monkeypatch.setattr(ns_cli.platform, "system", lambda: "Windows")
    dry_flags: list[bool] = []

    def fake_exec(_target: object, *, dry_run: bool, restore_winhttp: bool, run: object) -> dict[str, object]:
        dry_flags.append(bool(dry_run))
        assert restore_winhttp is True
        return {"success": True, "rollback_kind": "known_good_restore", "skipped": False}

    monkeypatch.setattr(ns_cli, "execute_known_good_proxy_restore", fake_exec)
    args = Namespace(repo_root=tmp_path, snapshot_name="p", confirm_phrase="", dry_run=False)
    assert ns_cli.cmd_network_state_restore(args) == 0
    assert dry_flags == [True, True]


def test_cli_network_state_snapshot_list_smoke(tmp_path: Path) -> None:
    append_snapshot(tmp_path, name="x", snapshot=_snap())
    code = cli_main(["--repo-root", str(tmp_path), "network-state", "snapshot", "list"])
    assert code == 0


def test_procmon_like_csv_filters_internet_settings(tmp_path: Path) -> None:
    csv_content = """Time of Day,Process Name,PID,Path,Detail
12:34:56,foo.exe,1,HKCU\\\\Software\\\\Microsoft\\\\Windows\\\\CurrentVersion\\\\Internet Settings\\\\ProxyEnable,{}
12:34:56,bar.exe,2,C:\\\\Other,{}
"""
    p = tmp_path / "ev.csv"
    p.write_text(csv_content, encoding="utf-8")
    rows = parse_procmon_like_csv(p)
    assert len(rows) == 1
    assert rows[0]["process_name"] == "foo.exe"
