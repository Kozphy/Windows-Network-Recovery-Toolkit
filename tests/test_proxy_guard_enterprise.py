from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.core.models import ProxyRegistrySnapshot
from src.proxy_guard.audit import emit_proxy_guard_audit
from src.proxy_guard.eventlog_attribution import attribution_from_windows_event_logs
from src.proxy_guard.guard_evaluation import evaluate_proxy_transition, hkcu_proxy_core_tuple
from src.proxy_guard.models import (
    AttributionResult,
    ProcessIdentity,
    ProxyGuardAuditRecord,
    ProxySnapshot,
    RollbackPlan,
    RollbackResult,
)
from src.proxy_guard.parser import parse_proxy_server
from src.proxy_guard.policy import ProxyGuardPolicy
from src.proxy_guard.process_attribution import resolve_attribution
from src.proxy_guard.rollback import execute_lkg_snapshot_rollback


def _pol(tmp: Path) -> ProxyGuardPolicy:
    return ProxyGuardPolicy(
        source_path=tmp / "p.json",
        allowed_process_name_substrings=(),
        allowed_process_names_exact=(),
        allow_when_attribution_empty=False,
        trusted_exe_paths=(),
        allowed_autoconfig_url_substrings=("corp",),
    )


def _snap(en: int, srv: str | None) -> ProxySnapshot:
    reg = ProxyRegistrySnapshot(
        proxy_enable=en,
        proxy_server=srv,
        auto_config_url=None,
        auto_detect=0,
        proxy_override=None,
    )
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
        captured_at="t",
    )


def test_detect_proxy_enable_change(tmp_path: Path) -> None:
    before = _snap(1, "10.0.0.1:80")
    after = _snap(0, "10.0.0.1:80")
    assert hkcu_proxy_core_tuple(before) != hkcu_proxy_core_tuple(after)


def test_detect_proxy_server_change(tmp_path: Path) -> None:
    before = _snap(1, "10.0.0.1:80")
    after = _snap(1, "10.0.0.2:8080")
    assert hkcu_proxy_core_tuple(before) != hkcu_proxy_core_tuple(after)


def test_unknown_process_blocked_on_loopback_without_listener(tmp_path: Path) -> None:
    before = _snap(0, None)
    after = _snap(1, "127.0.0.1:99999")
    pp = parse_proxy_server(after.proxy_server)
    attr = AttributionResult(
        mode="best_effort_process_snapshot",
        confidence="low",
        process=ProcessIdentity(
            pid=1,
            ppid=None,
            exe=r"C:\\tmp\\evil.exe",
            name="evil.exe",
            cmdline=None,
            create_time_utc=None,
            user=None,
            source="best_effort_listen_owner",
        ),
        evidence=(),
        limitations=("test",),
    )
    gd = evaluate_proxy_transition(
        prior_snap=before,
        curr_snap=after,
        parsed_prior=parse_proxy_server(before.proxy_server),
        parsed_after=pp,
        attribution=attr,
        policy=_pol(tmp_path),
        port_listen=False,
    )
    assert gd.decision == "blocked"


def test_trusted_exe_verified_eventlog_allowed(tmp_path: Path) -> None:
    pol = ProxyGuardPolicy(
        source_path=tmp_path / "p.json",
        allowed_process_name_substrings=(),
        allowed_process_names_exact=(),
        allow_when_attribution_empty=False,
        trusted_exe_paths=(r"c:\trusted\\",),
        allowed_autoconfig_url_substrings=(),
    )
    before = _snap(0, None)
    after = _snap(1, "127.0.0.1:7777")
    attr = AttributionResult(
        mode="verified_eventlog",
        confidence="verified",
        process=ProcessIdentity(
            pid=55,
            ppid=None,
            exe=r"C:\Trusted\App\svc.exe",
            name="svc.exe",
            cmdline=None,
            create_time_utc=None,
            user=None,
            source="eventlog_sysmon_registry",
        ),
        evidence=(),
        limitations=(),
    )
    gd = evaluate_proxy_transition(
        prior_snap=before,
        curr_snap=after,
        parsed_prior=parse_proxy_server(before.proxy_server),
        parsed_after=parse_proxy_server(after.proxy_server),
        attribution=attr,
        policy=pol,
        port_listen=False,
    )
    assert gd.decision == "allowed"


def test_dry_run_rollback_writes_audit(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    sinks: dict[str, list[dict[str, object]]] = {}

    def fake_append_jsonl(path: Path, blob: dict[str, object]) -> None:
        sinks.setdefault(path.name, []).append(blob)

    monkeypatch.setattr("src.proxy_guard.audit.append_jsonl", fake_append_jsonl)
    rr = ProxyGuardAuditRecord(
        schema_version=2,
        timestamp="x",
        event="t",
        before_snapshot={"a": 1},
        after_snapshot={"a": 2},
        attribution={"m": "best_effort_process_snapshot"},
        policy_decision={"decision": "blocked"},
        rollback_plan=RollbackPlan(
            dry_run_requested=True,
            restore_wininet=True,
            restore_winhttp=False,
            would_restore_git_or_env=False,
        ).to_jsonable(),
        rollback_result=RollbackResult(status="skipped_dry_run", detail="dry").to_jsonable(),
        safety_notes=("ok",),
    )
    emit_proxy_guard_audit(rr, repo_root=tmp_path)
    for name in ("proxy_guard_watch.jsonl", "proxy_guard_actions.jsonl", "proxy_guard_audit.jsonl"):
        assert len(sinks.get(name, [])) == 1
        blob = sinks[name][0]
        assert "before_snapshot" in blob


def test_lkg_snap_skipped(monkeypatch: pytest.MonkeyPatch) -> None:
    run_m = MagicMock()
    blob = execute_lkg_snapshot_rollback(None, dry_run=False, restore_winhttp=False, run=run_m)
    assert blob.get("skipped") is True


def test_lkg_invokes_registry_writer(monkeypatch: pytest.MonkeyPatch) -> None:
    spy = MagicMock(return_value=())
    monkeypatch.setattr("src.proxy_guard.rollback.apply_reg_argv_sequences", spy)
    lkg = _snap(0, None)
    execute_lkg_snapshot_rollback(lkg, dry_run=False, restore_winhttp=False, run=MagicMock())
    assert spy.called


def test_eventlog_fallback_best_effort(tmp_path: Path) -> None:
    owners = {"port": 1, "owners": [{"process_name": "x.exe", "pid": 2}], "notes": ()}
    with patch("src.proxy_guard.process_attribution.attribution_from_windows_event_logs", return_value=None):
        att = resolve_attribution(mode="eventlog", owners_payload=owners, run=MagicMock())
    assert att.mode == "best_effort_process_snapshot"
    assert "eventlog_mode_without_matching_sysmon_record" in att.limitations


def test_eventlog_verified(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = AttributionResult(
        mode="verified_eventlog",
        confidence="verified",
        process=None,
        evidence=(),
        limitations=(),
    )
    monkeypatch.setattr(
        "src.proxy_guard.process_attribution.attribution_from_windows_event_logs",
        lambda **_: fake,
    )
    att = resolve_attribution(mode="auto", owners_payload={"owners": [], "notes": []}, run=MagicMock())
    assert att.mode == "verified_eventlog"


def test_sysmon_stub_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    proc = MagicMock()
    proc.stdout = ""
    monkeypatch.setattr("subprocess.run", lambda *a, **k: proc)
    assert attribution_from_windows_event_logs(run=subprocess.run, mode="auto") is None


@pytest.mark.parametrize(
    ("port_listen", "owners", "blocked"),
    [
        (
            False,
            [{"process_name": "evil.exe", "pid": 1, "executable_path": r"C:\x\evil.exe"}],
            True,
        ),
        (
            True,
            [{"process_name": "helper.exe", "pid": 1, "executable_path": r"C:\x\helper.exe"}],
            False,
        ),
    ],
)
def test_loopback_listener_behavior(tmp_path: Path, port_listen: bool, owners: list[dict[str, object]], blocked: bool) -> None:
    before = _snap(0, None)
    after = _snap(1, "127.0.0.1:4545")
    pol = ProxyGuardPolicy(
        source_path=tmp_path / "p.json",
        allowed_process_name_substrings=("helper",) if port_listen else (),
        allowed_process_names_exact=(),
        allow_when_attribution_empty=False,
        trusted_exe_paths=(),
        allowed_autoconfig_url_substrings=("corp",),
    )
    attr = AttributionResult(
        mode="best_effort_process_snapshot",
        confidence="low",
        process=ProcessIdentity(
            pid=1,
            ppid=None,
            exe=str(owners[0].get("executable_path")),
            name=str(owners[0].get("process_name")),
            cmdline=None,
            create_time_utc=None,
            user=None,
            source="best_effort_listen_owner",
        ),
        evidence=(),
        limitations=(),
    )
    gd = evaluate_proxy_transition(
        prior_snap=before,
        curr_snap=after,
        parsed_prior=parse_proxy_server(before.proxy_server),
        parsed_after=parse_proxy_server(after.proxy_server),
        attribution=attr,
        policy=pol,
        port_listen=port_listen,
    )
    assert gd.decision == ("blocked" if blocked else "allowed")
