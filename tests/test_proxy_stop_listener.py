"""Tests for operator-confirmed stop-proxy-listener remediation."""

from __future__ import annotations

from argparse import Namespace
from pathlib import Path

import pytest

from src.proxy_guard.remediation import STOP_PROXY_LISTENER_PHRASE, get_remediation_action
from src.proxy_guard.stop_listener import (
    StopListenerTarget,
    build_taskkill_argv,
    evaluate_stop_listener_policy,
    execute_taskkill,
    resolve_stop_listener_target,
    run_stop_listener_workflow,
)


def test_stop_proxy_listener_action_is_allowlisted_not_kill_process() -> None:
    action = get_remediation_action("stop_proxy_listener")
    assert action is not None
    assert not action.blocked_reason
    assert action.required_confirmation == STOP_PROXY_LISTENER_PHRASE

    blocked = get_remediation_action("kill_process")
    assert blocked is not None
    assert blocked.blocked_reason


def test_confirmation_mismatch_blocks() -> None:
    target = StopListenerTarget(port=57324, pid=99, process_name="node.exe", parent_pid=1, parent_name="powershell.exe")
    decision, reason = evaluate_stop_listener_policy(
        dry_run=False,
        confirmation="WRONG",
        target=target,
        elevated=True,
    )
    assert decision == "BLOCK"
    assert reason == "confirmation_mismatch"


def test_missing_admin_blocks() -> None:
    target = StopListenerTarget(port=57324, pid=99, process_name="node.exe", parent_pid=1, parent_name="powershell.exe")
    decision, reason = evaluate_stop_listener_policy(
        dry_run=False,
        confirmation=STOP_PROXY_LISTENER_PHRASE,
        target=target,
        elevated=False,
    )
    assert decision == "BLOCK"
    assert reason == "administrator_elevation_required"


def test_no_listener_pid_blocks() -> None:
    decision, reason = evaluate_stop_listener_policy(
        dry_run=False,
        confirmation=STOP_PROXY_LISTENER_PHRASE,
        target=None,
        elevated=True,
    )
    assert decision == "BLOCK"
    assert reason == "no_listener_pid"


def test_dry_run_never_calls_taskkill(monkeypatch: pytest.MonkeyPatch) -> None:
    target = StopListenerTarget(port=57324, pid=99, process_name="node.exe", parent_pid=1, parent_name="powershell.exe")

    def fail_run(*_a, **_k):
        pytest.fail("taskkill must not run in dry-run")

    monkeypatch.setattr(
        "src.proxy_guard.stop_listener.resolve_stop_listener_target",
        lambda **_: (target, ()),
    )
    monkeypatch.setattr("src.proxy_guard.stop_listener.execute_taskkill", fail_run)

    result = run_stop_listener_workflow(dry_run=True, confirmation="", run=fail_run)
    assert result.decision == "PREVIEW"
    assert result.mutated is False
    assert result.planned_argv == build_taskkill_argv(99)


def test_policy_allow_path_executes_taskkill_with_mocks(monkeypatch: pytest.MonkeyPatch) -> None:
    target = StopListenerTarget(port=57324, pid=42, process_name="node.exe", parent_pid=7, parent_name="powershell.exe")
    calls: list[int] = []

    def fake_taskkill(pid: int, *, run=None):
        calls.append(pid)
        return {"argv": list(build_taskkill_argv(pid)), "returncode": 0, "stdout": "OK", "stderr": "", "success": True}

    monkeypatch.setattr(
        "src.proxy_guard.stop_listener.resolve_stop_listener_target",
        lambda **_: (target, ()),
    )
    monkeypatch.setattr("src.proxy_guard.stop_listener.execute_taskkill", fake_taskkill)

    result = run_stop_listener_workflow(
        dry_run=False,
        confirmation=STOP_PROXY_LISTENER_PHRASE,
        elevated=True,
    )
    assert result.decision == "ALLOW"
    assert result.mutated is True
    assert calls == [42]


def test_resolve_stop_listener_target_without_owners(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "src.proxy_guard.stop_listener.read_proxy_registry",
        lambda **_: type("R", (), {"proxy_server": "127.0.0.1:57324"})(),
    )
    monkeypatch.setattr(
        "src.proxy_guard.stop_listener.resolve_localhost_proxy_owners",
        lambda *_a, **_k: ((), ("No LISTENING rows found for port 57324 in netstat snapshot.",)),
    )
    target, notes = resolve_stop_listener_target(port=None)
    assert target is None
    assert any("57324" in n for n in notes)


def test_cmd_proxy_stop_listener_dry_run_writes_audit(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    repo = tmp_path
    target = StopListenerTarget(port=57324, pid=55, process_name="node.exe", parent_pid=1, parent_name="powershell.exe")
    written: list[dict[str, object]] = []

    monkeypatch.setattr("src.command_handlers._repo_root", lambda _p=None: repo)
    monkeypatch.setattr(
        "src.command_handlers.run_stop_listener_workflow",
        lambda **_: run_stop_listener_workflow(dry_run=True, confirmation="", elevated=True),
    )
    monkeypatch.setattr(
        "src.proxy_guard.stop_listener.resolve_stop_listener_target",
        lambda **_: (target, ()),
    )
    monkeypatch.setattr("src.command_handlers.append_jsonl_core", lambda _path, payload: written.append(dict(payload)))

    from src.command_handlers import cmd_proxy_stop_listener

    rc = cmd_proxy_stop_listener(Namespace(repo_root=repo, dry_run=True, stop_listener_confirm_phrase="", emit_json=False))
    assert rc == 0
    assert written[-1]["subtype"] == "proxy_stop_listener"


def test_execute_taskkill_builds_argv() -> None:
    assert build_taskkill_argv(123) == ("taskkill", "/F", "/PID", "123", "/T")

    class Proc:
        returncode = 0
        stdout = "SUCCESS"
        stderr = ""

    result = execute_taskkill(5, run=lambda *_a, **_k: Proc())
    assert result["success"] is True
    assert result["argv"][3] == "5"
