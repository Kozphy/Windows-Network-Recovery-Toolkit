"""Tests for gated Edge/Chrome cold-start (QUIC/IPv6 stall)."""

from __future__ import annotations

from pathlib import Path

from src.proxy_drift.browser_stall import CONFIRM_RESTART_BROWSER, run_browser_stall_fix
from windows_network_toolkit.safety import is_blocked_action


def test_preview_default_does_not_apply(tmp_path: Path) -> None:
    applied: list[str] = []

    def _apply(**_k):
        applied.append("x")
        return {"steps": [], "errors": []}

    out = run_browser_stall_fix(
        dry_run=True,
        confirm="",
        repo_root=tmp_path,
        apply_fn=_apply,
        audit_path=tmp_path / "a.jsonl",
    )
    assert out["action_taken"] == "preview_only"
    assert applied == []
    assert CONFIRM_RESTART_BROWSER in (out.get("confirmation_required") or "")


def test_blocked_without_token(tmp_path: Path) -> None:
    applied: list[str] = []

    def _apply(**_k):
        applied.append("x")
        return {"steps": ["ok"], "errors": []}

    out = run_browser_stall_fix(
        dry_run=False,
        confirm="WRONG",
        repo_root=tmp_path,
        apply_fn=_apply,
        audit_path=tmp_path / "a.jsonl",
    )
    assert out["action_taken"] == "blocked"
    assert applied == []


def test_apply_with_token(tmp_path: Path) -> None:
    def _apply(*, run, include_webview, open_url):
        assert include_webview is False
        assert "youtube" in open_url
        return {"steps": ["Stopped msedge.exe", "Launched msedge.exe"], "errors": [], "launched": "msedge"}

    out = run_browser_stall_fix(
        dry_run=False,
        confirm=CONFIRM_RESTART_BROWSER,
        repo_root=tmp_path,
        apply_fn=_apply,
        audit_path=tmp_path / "a.jsonl",
    )
    assert out["action_taken"] == "remediated"


def test_kill_proxy_process_still_blocked() -> None:
    assert is_blocked_action("KILL_PROXY_PROCESS")
