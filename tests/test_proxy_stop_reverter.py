"""Tests for operator-confirmed stop-proxy-reverter remediation."""

from __future__ import annotations

from argparse import Namespace
from pathlib import Path

import pytest

from src.proxy_guard.remediation import STOP_PROXY_REVERTER_PHRASE, get_remediation_action
from src.proxy_guard.stop_listener import StopListenerTarget, build_taskkill_argv
from src.proxy_guard.stop_reverter import (
    evaluate_stop_reverter_policy,
    is_eligible_reverter_parent,
    resolve_reverter_parent_pid,
    run_stop_reverter_workflow,
)


def test_stop_proxy_reverter_action_is_allowlisted_not_kill_process() -> None:
    action = get_remediation_action("stop_proxy_reverter")
    assert action is not None
    assert not action.blocked_reason
    assert action.required_confirmation == STOP_PROXY_REVERTER_PHRASE

    blocked = get_remediation_action("kill_process")
    assert blocked is not None
    assert blocked.blocked_reason


def test_eligible_parent_names() -> None:
    assert is_eligible_reverter_parent("powershell.exe")
    assert is_eligible_reverter_parent("pwsh.exe")
    assert not is_eligible_reverter_parent("node.exe")


def test_confirmation_mismatch_blocks() -> None:
    target = StopListenerTarget(
        port=57324,
        pid=99,
        process_name="node.exe",
        parent_pid=34092,
        parent_name="powershell.exe",
    )
    decision, reason = evaluate_stop_reverter_policy(
        dry_run=False,
        confirmation="WRONG",
        target=target,
        parent_pid=34092,
        elevated=True,
    )
    assert decision == "BLOCK"
    assert reason == "confirmation_mismatch"


def test_missing_admin_blocks() -> None:
    target = StopListenerTarget(
        port=57324,
        pid=99,
        process_name="node.exe",
        parent_pid=34092,
        parent_name="powershell.exe",
    )
    decision, reason = evaluate_stop_reverter_policy(
        dry_run=False,
        confirmation=STOP_PROXY_REVERTER_PHRASE,
        target=target,
        parent_pid=34092,
        elevated=False,
    )
    assert decision == "BLOCK"
    assert reason == "administrator_elevation_required"


def test_no_eligible_parent_blocks() -> None:
    target = StopListenerTarget(
        port=57324,
        pid=99,
        process_name="node.exe",
        parent_pid=1,
        parent_name="node.exe",
    )
    assert resolve_reverter_parent_pid(target) is None
    decision, reason = evaluate_stop_reverter_policy(
        dry_run=False,
        confirmation=STOP_PROXY_REVERTER_PHRASE,
        target=target,
        parent_pid=None,
        elevated=True,
    )
    assert decision == "BLOCK"
    assert reason == "no_eligible_parent_pid"


def test_dry_run_never_calls_taskkill(monkeypatch: pytest.MonkeyPatch) -> None:
    target = StopListenerTarget(
        port=57324,
        pid=99,
        process_name="node.exe",
        parent_pid=34092,
        parent_name="powershell.exe",
    )

    def fail_run(*_a, **_k):
        pytest.fail("taskkill must not run in dry-run")

    monkeypatch.setattr(
        "src.proxy_guard.stop_reverter.resolve_stop_listener_target",
        lambda **_: (target, ()),
    )
    monkeypatch.setattr("src.proxy_guard.stop_reverter.execute_taskkill", fail_run)

    result = run_stop_reverter_workflow(dry_run=True, confirmation="", run=fail_run)
    assert result.decision == "PREVIEW"
    assert result.mutated is False
    assert result.planned_argv == build_taskkill_argv(34092)


def test_policy_allow_path_kills_parent_with_mocks(monkeypatch: pytest.MonkeyPatch) -> None:
    target = StopListenerTarget(
        port=57324,
        pid=42,
        process_name="node.exe",
        parent_pid=34092,
        parent_name="powershell.exe",
    )
    calls: list[int] = []

    def fake_taskkill(pid: int, *, run=None):
        calls.append(pid)
        return {
            "argv": list(build_taskkill_argv(pid)),
            "returncode": 0,
            "stdout": "OK",
            "stderr": "",
            "success": True,
        }

    monkeypatch.setattr(
        "src.proxy_guard.stop_reverter.resolve_stop_listener_target",
        lambda **_: (target, ()),
    )
    monkeypatch.setattr("src.proxy_guard.stop_reverter.execute_taskkill", fake_taskkill)

    result = run_stop_reverter_workflow(
        dry_run=False,
        confirmation=STOP_PROXY_REVERTER_PHRASE,
        elevated=True,
    )
    assert result.decision == "ALLOW"
    assert result.mutated is True
    assert calls == [34092]


def test_stop_listener_stop_parent_requires_reverter_confirm(monkeypatch: pytest.MonkeyPatch) -> None:
    from src.proxy_guard.stop_listener import run_stop_listener_workflow

    target = StopListenerTarget(
        port=57324,
        pid=42,
        process_name="node.exe",
        parent_pid=34092,
        parent_name="powershell.exe",
    )
    calls: list[int] = []

    def fake_taskkill(pid: int, *, run=None):
        calls.append(pid)
        return {"argv": list(build_taskkill_argv(pid)), "returncode": 0, "stdout": "", "stderr": "", "success": True}

    monkeypatch.setattr(
        "src.proxy_guard.stop_listener.resolve_stop_listener_target",
        lambda **_: (target, ()),
    )
    monkeypatch.setattr("src.proxy_guard.stop_listener.execute_taskkill", fake_taskkill)

    blocked = run_stop_listener_workflow(
        dry_run=False,
        confirmation="STOP_PROXY_LISTENER",
        stop_parent_tree=True,
        reverter_confirmation="",
        elevated=True,
    )
    assert blocked.decision == "BLOCK"
    assert blocked.reason == "missing_confirmation"
    assert calls == []

    ok = run_stop_listener_workflow(
        dry_run=False,
        confirmation="STOP_PROXY_LISTENER",
        stop_parent_tree=True,
        reverter_confirmation=STOP_PROXY_REVERTER_PHRASE,
        elevated=True,
    )
    assert ok.decision == "ALLOW"
    assert ok.mutated is True
    assert calls == [34092, 42]


def test_cmd_proxy_stop_reverter_dry_run_writes_audit(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    repo = tmp_path
    target = StopListenerTarget(
        port=57324,
        pid=55,
        process_name="node.exe",
        parent_pid=34092,
        parent_name="powershell.exe",
    )
    written: list[dict[str, object]] = []

    monkeypatch.setattr("src.command_handlers._repo_root", lambda _p=None: repo)
    monkeypatch.setattr(
        "src.proxy_guard.stop_reverter.resolve_stop_listener_target",
        lambda **_: (target, ()),
    )
    monkeypatch.setattr("src.command_handlers.append_jsonl_core", lambda _path, payload: written.append(dict(payload)))

    from src.command_handlers import cmd_proxy_stop_reverter

    rc = cmd_proxy_stop_reverter(
        Namespace(repo_root=repo, dry_run=True, stop_reverter_confirm_phrase="", emit_json=False)
    )
    assert rc == 0
    assert written[-1]["subtype"] == "proxy_stop_reverter"
