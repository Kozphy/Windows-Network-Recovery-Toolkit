"""Confirmation gate for ``python -m src proxy restore-lkg`` (typed phrase, allowlist, LKG)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.command_handlers_safety import cmd_proxy_restore_lkg  # noqa: E402
from src.proxy_guard.known_good_store import append_named_snapshot  # noqa: E402
from src.proxy_guard.models import ProxySnapshot  # noqa: E402


def _make_snapshot() -> ProxySnapshot:
    return ProxySnapshot(
        proxy_enable=1,
        proxy_server="127.0.0.1:7890",
        proxy_override=None,
        auto_config_url=None,
        auto_detect=0,
        winhttp_proxy="Direct access (no proxy server).",
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
        captured_at="2026-05-09T11:30:00+00:00",
    )


def _ns(**fields: Any) -> argparse.Namespace:
    namespace = argparse.Namespace(
        repo_root=fields.pop("repo_root", None),
        emit_json=True,
        snapshot_name=fields.pop("snapshot_name", ""),
        dry_run=fields.pop("dry_run", True),
        confirm_phrase=fields.pop("confirm_phrase", ""),
    )
    for key, value in fields.items():
        setattr(namespace, key, value)
    return namespace


def test_restore_lkg_blocks_when_no_snapshot(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    rc = cmd_proxy_restore_lkg(_ns(repo_root=tmp_path, dry_run=True))
    assert rc == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["decision"] == "BLOCK"
    assert payload["reason"] == "no_lkg_snapshot_available"
    assert payload["mutated"] is False


def test_restore_lkg_dry_run_returns_preview_with_audit(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    append_named_snapshot(tmp_path, name="known_good", snapshot=_make_snapshot())
    rc = cmd_proxy_restore_lkg(_ns(repo_root=tmp_path, dry_run=True))
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["decision"] == "PREVIEW"
    assert payload["mutated"] is False
    assert payload["audit_event_id"]
    audit_path = tmp_path / "logs" / "safety_audit.jsonl"
    audit_rows = [json.loads(line) for line in audit_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert any(row["event_kind"] == "preview_requested" for row in audit_rows)


def test_restore_lkg_blocks_missing_confirmation(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    append_named_snapshot(tmp_path, name="known_good", snapshot=_make_snapshot())
    rc = cmd_proxy_restore_lkg(_ns(repo_root=tmp_path, dry_run=False, confirm_phrase=""))
    assert rc == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["decision"] == "BLOCK"
    assert payload["reason"] == "missing_confirmation"
    audit_rows = [
        json.loads(line)
        for line in (tmp_path / "logs" / "safety_audit.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert any(row["event_kind"] == "blocked_missing_confirmation" for row in audit_rows)


def test_restore_lkg_blocks_wrong_confirmation(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    append_named_snapshot(tmp_path, name="known_good", snapshot=_make_snapshot())
    rc = cmd_proxy_restore_lkg(_ns(repo_root=tmp_path, dry_run=False, confirm_phrase="WRONG_PHRASE"))
    assert rc == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["decision"] == "BLOCK"
    assert payload["reason"] == "confirmation_mismatch"
    audit_rows = [
        json.loads(line)
        for line in (tmp_path / "logs" / "safety_audit.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert any(row["event_kind"] == "blocked_wrong_confirmation" for row in audit_rows)


def test_restore_lkg_with_confirmation_planned_action_lists_only_wininet_fields(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    append_named_snapshot(tmp_path, name="known_good", snapshot=_make_snapshot())
    rc = cmd_proxy_restore_lkg(
        _ns(repo_root=tmp_path, dry_run=True, confirm_phrase="RESTORE_WININET_PROXY_FROM_LKG")
    )
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    requested_fields = payload["planned_action"]["requested_registry_fields"]
    assert set(requested_fields) <= {"ProxyEnable", "ProxyServer", "AutoConfigURL", "ProxyOverride", "AutoDetect"}
    for argv in payload["planned_action"]["mutation_argv"]:
        joined = " ".join(argv)
        assert "Internet Settings" in joined
        for blocked_token in ("netsh advfirewall", "taskkill", "Disable-NetAdapter", "certutil"):
            assert blocked_token not in joined
