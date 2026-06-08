"""Offline tests for named last-known-good snapshots (storage, diff, argv-only restore)."""

from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.core.models import ProxyRegistrySnapshot
from src.proxy_guard import proxy_snapshot_commands as psc_cmds
from src.proxy_guard import snapshot_capture as snap_cap
from src.proxy_guard.known_good_diff import diff_snapshots
from src.proxy_guard.known_good_store import (
    append_named_snapshot,
    get_latest_named_record,
    list_snapshot_summaries,
)
from src.proxy_guard.models import ProxySnapshot
from src.proxy_guard.rollback import execute_known_good_proxy_restore


def _snap(**overrides: object) -> ProxySnapshot:
    base = dict(
        proxy_enable=0,
        proxy_server=None,
        proxy_override=None,
        auto_config_url=None,
        auto_detect=0,
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
    base.update(overrides)
    return ProxySnapshot(**base)


def test_append_and_get_latest_named(tmp_path: Path) -> None:
    s = _snap(proxy_server="10.0.0.2:8080")
    row = append_named_snapshot(tmp_path, name="corp", snapshot=s)
    assert row["name"] == "corp"
    got = get_latest_named_record(tmp_path, "corp")
    assert got and got["snapshot"]["proxy_server"] == "10.0.0.2:8080"
    summaries = list_snapshot_summaries(tmp_path)
    assert len(summaries) == 1
    append_named_snapshot(tmp_path, name="corp", snapshot=_snap(proxy_server="10.0.0.3:8080"))
    summaries2 = list_snapshot_summaries(tmp_path)
    assert len(summaries2) == 1
    got2 = get_latest_named_record(tmp_path, "corp")
    assert got2 and got2["snapshot"]["proxy_server"] == "10.0.0.3:8080"


def test_diff_only_changed_loopback_hint() -> None:
    saved = _snap(proxy_enable=1, proxy_server="old:80")
    cur = _snap(proxy_enable=1, proxy_server="127.0.0.1:9999")
    d = diff_snapshots(saved, cur)
    assert "proxy_server" in d["changed_fields"]
    assert d["suspicious_loopback_hints"]


def test_execute_known_good_dry_run_no_subprocess_writes() -> None:
    fake = MagicMock(side_effect=AssertionError("subprocess.run should not be invoked in dry_run"))
    target = _snap(proxy_enable=0, git_http_proxy="http://legacy:3128/")
    result = execute_known_good_proxy_restore(target, dry_run=True, restore_winhttp=True, run=fake)
    assert result.get("skipped") is False
    for row in result.get("git_audits") or []:
        assert row["stdout"] == "[dry-run] not executed"


def test_execute_known_good_argv_shapes() -> None:
    logs: list[list[str]] = []

    def capturing_run(argv, **_k):
        logs.append(list(argv))

        class P:
            returncode = 0
            stdout = ""
            stderr = ""

        return P()

    target = _snap(
        git_http_proxy="",
        npm_proxy="corp:8080",
        user_http_proxy="http://proxy:1/",
    )
    execute_known_good_proxy_restore(target, dry_run=False, restore_winhttp=False, run=capturing_run)
    flat = " ".join(" ".join(x) for x in logs)
    assert "git" in flat and "unset-all" in flat
    assert "npm" in flat and "config" in flat
    assert "HKCU\\Environment" in flat or r"HKCU\Environment" in flat


def test_capture_proxy_snapshot_injected_registry_skips_live_probe(monkeypatch: pytest.MonkeyPatch) -> None:
    reg = ProxyRegistrySnapshot(
        proxy_enable=1,
        proxy_server="corp.example.invalid:3128",
        auto_config_url=None,
        auto_detect=0,
        proxy_override="<local>;*.internal",
    )
    monkeypatch.setattr(snap_cap, "_capture_winhttp_stdout", lambda run: "Direct access (no proxy server).\n")
    monkeypatch.setattr(snap_cap, "_user_env_optional", lambda _n: None)

    def boom_run(*_a: object, **_k: object) -> object:
        raise AssertionError("live subprocess.reg probe should not run when registry_snapshot is passed")

    snap = snap_cap.capture_proxy_snapshot(
        run=boom_run,
        registry_snapshot=reg,
        skip_optional_cli=True,
    )
    assert snap.proxy_enable == 1
    assert snap.proxy_server == "corp.example.invalid:3128"
    assert snap.proxy_override == "<local>;*.internal"
    assert snap.winhttp_direct_access is True


def test_cmd_proxy_snapshot_save_uses_fake_collector(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(psc_cmds.platform, "system", lambda: "Windows")
    monkeypatch.setattr(psc_cmds, "capture_proxy_snapshot", lambda **kw: _snap(proxy_server="saved:8080"))

    args = Namespace(repo_root=tmp_path, snapshot_name="baseline", as_default=False)
    assert psc_cmds.cmd_proxy_snapshot_save(args) == 0
    row = json.loads((tmp_path / "logs" / "proxy_known_good_snapshots.jsonl").read_text().strip())
    assert row["name"] == "baseline"
    assert row["snapshot"]["proxy_server"] == "saved:8080"


def test_cmd_proxy_snapshot_diff_uses_fake_current(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    append_named_snapshot(tmp_path, name="b", snapshot=_snap(proxy_server="stable:80"))
    monkeypatch.setattr(psc_cmds.platform, "system", lambda: "Windows")
    monkeypatch.setattr(psc_cmds, "capture_proxy_snapshot", lambda **kw: _snap(proxy_server="127.0.0.1:7777"))

    args = Namespace(repo_root=tmp_path, snapshot_name="b")
    assert psc_cmds.cmd_proxy_snapshot_diff(args) == 0


def test_cmd_proxy_snapshot_restore_writes_audit_fake_writer(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    append_named_snapshot(tmp_path, name="r", snapshot=_snap(proxy_enable=0))
    monkeypatch.setattr(psc_cmds.platform, "system", lambda: "Windows")

    def fake_restore(_target: object, *, dry_run: bool, restore_winhttp: bool, run: object) -> dict[str, object]:
        assert dry_run is True
        return {"success": True, "skipped": False, "rollback_kind": "known_good_restore"}

    monkeypatch.setattr(psc_cmds, "execute_known_good_proxy_restore", fake_restore)
    args = Namespace(repo_root=tmp_path, snapshot_name="r", confirm_phrase="", dry_run=False)
    assert psc_cmds.cmd_proxy_snapshot_restore(args) == 0
    aj = tmp_path / "logs" / "proxy_guard_actions.jsonl"
    line = aj.read_text(encoding="utf-8").strip().splitlines()[-1]
    row = json.loads(line)
    assert row["action"] == "proxy_known_good_restore"
    assert row["result"] == "dry_run_preview"


def test_restore_forced_dry_run_overrides_confirm(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    append_named_snapshot(tmp_path, name="x", snapshot=_snap())
    monkeypatch.setattr(psc_cmds.platform, "system", lambda: "Windows")
    phases: list[bool] = []

    def fake_restore(_target: object, *, dry_run: bool, restore_winhttp: bool, run: object) -> dict[str, object]:
        phases.append(dry_run)
        return {"success": True, "skipped": False, "rollback_kind": "known_good_restore"}

    monkeypatch.setattr(psc_cmds, "execute_known_good_proxy_restore", fake_restore)
    args = Namespace(
        repo_root=tmp_path,
        snapshot_name="x",
        confirm_phrase=psc_cmds.KNOWN_GOOD_RESTORE_PHRASE,
        dry_run=True,
    )
    assert psc_cmds.cmd_proxy_snapshot_restore(args) == 0
    assert phases == [True]
