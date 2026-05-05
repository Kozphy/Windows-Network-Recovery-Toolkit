from __future__ import annotations

from pathlib import Path

from src.proxy_guard.connectivity import (
    CommandProbeResult,
    ConnectivitySnapshot,
    compare_connectivity,
)
from src.proxy_guard.decision import finalize_decision
from src.proxy_guard.guard_evaluation import evaluate_proxy_transition
from src.proxy_guard.models import AttributionResult, ProcessIdentity, ProxySnapshot
from src.proxy_guard.parser import parse_proxy_server
from src.proxy_guard.policy import ProxyGuardPolicy
from src.proxy_guard.rollback import build_wininet_restore_argv_list


def _snap(en: int, srv: str | None) -> ProxySnapshot:
    return ProxySnapshot(
        proxy_enable=en,
        proxy_server=srv,
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
        captured_at="2026-01-01T00:00:00Z",
    )


def _probe(name: str, ok: bool) -> CommandProbeResult:
    return CommandProbeResult(name=name, ok=ok, returncode=0 if ok else 1, stdout="", stderr="")


def _conn(https_ok: bool, tcp_ok: bool = True, dns_ok: bool = True) -> ConnectivitySnapshot:
    return ConnectivitySnapshot(
        tcp_443_google=_probe("tcp", tcp_ok),
        https_google=_probe("https_google", https_ok),
        https_microsoft=_probe("https_microsoft", https_ok),
        dns_google=_probe("dns", dns_ok),
        wininet_proxy_enable=1,
        wininet_proxy_server="127.0.0.1:56397",
    )


def _policy(tmp_path: Path) -> ProxyGuardPolicy:
    return ProxyGuardPolicy(
        source_path=tmp_path / "policy.json",
        allowed_process_name_substrings=(),
        allowed_process_names_exact=(),
        allow_when_attribution_empty=False,
    )


def test_allowed_no_regression_localhost_listener(tmp_path: Path) -> None:
    before = _snap(1, "127.0.0.1:56397")
    after = _snap(0, "127.0.0.1:56397")
    attr = AttributionResult(mode="best_effort_process_snapshot", confidence="low", process=None)
    gd = evaluate_proxy_transition(
        prior_snap=before,
        curr_snap=after,
        parsed_prior=parse_proxy_server(before.proxy_server),
        parsed_after=parse_proxy_server(after.proxy_server),
        attribution=attr,
        policy=_policy(tmp_path),
        port_listen=True,
    )
    validation = compare_connectivity(pre_change=_conn(True), post_change=_conn(True))
    final = finalize_decision(
        policy_decision=gd,
        connectivity_validation=validation,
        attribution=attr,
        parsed_is_localhost=True,
    )
    assert final["decision"] == "allowed_no_regression"
    assert final["risk_level"] == "low"
    assert final["recommended_action"] == "none"


def test_allowed_but_connectivity_regressed_when_https_fails(tmp_path: Path) -> None:
    before = _snap(1, "127.0.0.1:56397")
    after = _snap(0, "127.0.0.1:56397")
    attr = AttributionResult(mode="best_effort_process_snapshot", confidence="low", process=None)
    gd = evaluate_proxy_transition(
        prior_snap=before,
        curr_snap=after,
        parsed_prior=parse_proxy_server(before.proxy_server),
        parsed_after=parse_proxy_server(after.proxy_server),
        attribution=attr,
        policy=_policy(tmp_path),
        port_listen=True,
    )
    validation = compare_connectivity(pre_change=_conn(True, tcp_ok=True), post_change=_conn(False, tcp_ok=True))
    final = finalize_decision(
        policy_decision=gd,
        connectivity_validation=validation,
        attribution=attr,
        parsed_is_localhost=True,
    )
    assert final["decision"] == "allowed_but_connectivity_regressed"
    assert final["risk_level"] == "medium"
    assert final["recommended_action"] == "restore_previous_proxy_or_prompt_user"


def test_attribution_language_not_proof_without_sysmon(tmp_path: Path) -> None:
    before = _snap(0, None)
    after = _snap(1, "127.0.0.1:56397")
    attr = AttributionResult(
        mode="best_effort_process_snapshot",
        confidence="low",
        process=ProcessIdentity(
            pid=10,
            ppid=1,
            exe=r"C:\node\node.exe",
            name="node.exe",
            cmdline="node proxy.js",
            create_time_utc=None,
            user=None,
            source="best_effort_listen_owner",
        ),
    )
    gd = evaluate_proxy_transition(
        prior_snap=before,
        curr_snap=after,
        parsed_prior=parse_proxy_server(before.proxy_server),
        parsed_after=parse_proxy_server(after.proxy_server),
        attribution=attr,
        policy=_policy(tmp_path),
        port_listen=True,
    )
    final = finalize_decision(
        policy_decision=gd,
        connectivity_validation=compare_connectivity(pre_change=_conn(True), post_change=_conn(True)),
        attribution=attr,
        parsed_is_localhost=True,
    )
    notes = " ".join(final["attribution"]["notes"])
    assert "does not prove registry writer" in notes
    assert final["attribution"]["confidence"] in {"low", "medium"}


def test_non_local_suspicious_proxy_regression_high_risk(tmp_path: Path) -> None:
    before = _snap(0, None)
    after = _snap(1, "203.0.113.9:8080")
    attr = AttributionResult(mode="unknown", confidence="unknown", process=None)
    gd = evaluate_proxy_transition(
        prior_snap=before,
        curr_snap=after,
        parsed_prior=parse_proxy_server(before.proxy_server),
        parsed_after=parse_proxy_server(after.proxy_server),
        attribution=attr,
        policy=_policy(tmp_path),
        port_listen=False,
    )
    final = finalize_decision(
        policy_decision=gd,
        connectivity_validation=compare_connectivity(pre_change=_conn(True), post_change=_conn(False)),
        attribution=attr,
        parsed_is_localhost=False,
    )
    assert final["risk_level"] == "high"
    assert final["recommended_action"] in {"rollback_recommended", "prompt_user"}


def test_rollback_preview_targets_proxy_fields_only() -> None:
    snap = _snap(1, "127.0.0.1:8080")
    argv = build_wininet_restore_argv_list(snap)
    touched = " ".join(" ".join(row) for row in argv)
    assert "ProxyEnable" in touched
    assert "ProxyServer" in touched
    assert "AutoConfigURL" in touched
    assert "ProxyOverride" in touched
    assert "AutoDetect" not in touched

