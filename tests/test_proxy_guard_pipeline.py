"""Pipeline unit tests — diff, verify, attribution fallback, rollback preview payloads."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.core.models import ProxyRegistrySnapshot
from src.proxy_guard.attribution import (
    enhance_attribution_for_pipeline,
    wmi_like_process_snapshot,
)
from src.proxy_guard.diff import (
    proxy_state_audit_dict,
    verify_hkcu_core_matches_prior,
    wininet_argv_restored_fields,
)
from src.proxy_guard.guard_evaluation import evaluate_proxy_transition, hkcu_proxy_core_tuple
from src.proxy_guard.models import AttributionResult, ProxyGuardPolicyDecision, ProxySnapshot
from src.proxy_guard.parser import parse_proxy_server
from src.proxy_guard.pipeline import rollback_payload_for_audit, summarize_stdout_event
from src.proxy_guard.policy import ProxyGuardPolicy
from src.proxy_guard.rollback import execute_lkg_snapshot_rollback


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


def test_verify_hkcu_core_matches_prior() -> None:
    prior = _snap(0, None)
    reg = ProxyRegistrySnapshot(
        proxy_enable=0,
        proxy_server=None,
        auto_config_url=None,
        auto_detect=0,
        proxy_override=None,
    )
    assert verify_hkcu_core_matches_prior(reg, prior_target=prior) is True
    bad = ProxyRegistrySnapshot(
        proxy_enable=1,
        proxy_server=None,
        auto_config_url=None,
        auto_detect=0,
        proxy_override=None,
    )
    assert verify_hkcu_core_matches_prior(bad, prior_target=prior) is False


def test_wininet_argv_restored_fields_parses_reg_argv() -> None:
    audit = [{"argv": ["reg", "add", "HKCU\\...", "/v", "ProxyEnable", "/t", "REG_DWORD"], "returncode": 0}]
    names = wininet_argv_restored_fields(audit)
    assert "ProxyEnable" in names


def test_proxy_state_audit_keys() -> None:
    blob = proxy_state_audit_dict(_snap(1, "127.0.0.1:1"))
    assert blob["proxy_enable"] == 1
    assert "proxy_server" in blob


def test_disable_transition_not_blocked(tmp_path: Path) -> None:
    before = _snap(1, "10.0.0.1:80")
    after = _snap(0, "10.0.0.1:80")
    attr = AttributionResult(mode="unknown", confidence="unknown", process=None)
    gd = evaluate_proxy_transition(
        prior_snap=before,
        curr_snap=after,
        parsed_prior=parse_proxy_server(before.proxy_server),
        parsed_after=parse_proxy_server(after.proxy_server),
        attribution=attr,
        policy=ProxyGuardPolicy(
            source_path=tmp_path / "z.json",
            allowed_process_name_substrings=(),
            allowed_process_names_exact=(),
            allow_when_attribution_empty=False,
            observe_only_when_unknown_attribution=False,
        ),
        port_listen=None,
    )
    assert gd.decision == "allowed"


def test_observe_unknown_attribution_when_policy_flag(tmp_path: Path) -> None:
    before = _snap(0, None)
    after = _snap(1, "203.0.113.10:8080")  # non-loopback avoids localhost branch noise
    attr = AttributionResult(mode="unknown", confidence="unknown", process=None)
    pol = ProxyGuardPolicy(
        source_path=tmp_path / "z.json",
        allowed_process_name_substrings=(),
        allowed_process_names_exact=(),
        allow_when_attribution_empty=False,
        observe_only_when_unknown_attribution=True,
    )
    gd = evaluate_proxy_transition(
        prior_snap=before,
        curr_snap=after,
        parsed_prior=parse_proxy_server(before.proxy_server),
        parsed_after=parse_proxy_server(after.proxy_server),
        attribution=attr,
        policy=pol,
        port_listen=None,
    )
    assert gd.decision == "observe"


def test_summarize_stdout_includes_nested_rollback() -> None:
    gd = ProxyGuardPolicyDecision(
        decision="blocked",
        reason="x",
        matched_rule=None,
        rollback_allowed=True,
        rollback_required=False,
    )
    rb = rollback_payload_for_audit(
        action="rollback_preview",
        restored_fields=["ProxyEnable"],
        verification="not_run",
        error=None,
    )
    out = summarize_stdout_event(
        gd,
        rollback_subtree=rb,
        curr_snap=_snap(1, ""),
        parsed_after=parse_proxy_server(None),
    )
    assert out["rollback"]["action"] == "rollback_preview"


def test_wmi_like_process_snapshot_empty_on_failure() -> None:
    proc = MagicMock(returncode=1, stdout="{}", stderr="x")
    assert wmi_like_process_snapshot(run=lambda *a, **k: proc) == []


def test_enhance_attribution_no_wmi_keeps_unknown(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "src.proxy_guard.attribution.wmi_like_process_snapshot",
        lambda **_: [],
    )
    base = AttributionResult(mode="unknown", confidence="unknown", process=None)
    merged, hx = enhance_attribution_for_pipeline(
        base=base,
        owners_payload={"owners": [], "notes": []},
        run=subprocess.run,
    )
    assert hx is False
    assert merged.process is None


def test_prior_snapshot_rollback_calls_reg_writer(monkeypatch: pytest.MonkeyPatch) -> None:
    spy = MagicMock(return_value=())
    monkeypatch.setattr("src.proxy_guard.rollback.apply_reg_argv_sequences", spy)
    snap = _snap(0, None)
    blob = execute_lkg_snapshot_rollback(snap, dry_run=True, restore_winhttp=False, run=MagicMock())
    assert not blob.get("skipped")
    assert spy.called


def test_unified_pipeline_audit_keys(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from src.proxy_guard.audit import emit_pipeline_audit_v1

    captured: list[dict] = []

    monkeypatch.setattr("src.proxy_guard.audit.append_jsonl", lambda _p, blob: captured.append(blob))
    prev = proxy_state_audit_dict(_snap(0, None))
    post = proxy_state_audit_dict(_snap(1, "127.0.0.1:9"))
    payload = {
        "schema_version": "1",
        "event": "proxy_change_detected",
        "timestamp": "ts",
        "before": prev,
        "after": post,
        "attribute": {},
        "policy": {"decision": "blocked"},
        "rollback": rollback_payload_for_audit(
            action="rollback_preview",
            restored_fields=[],
            verification="not_run",
            error=None,
        ),
    }
    emit_pipeline_audit_v1(tmp_path, payload)
    assert captured
    loaded = captured[0]
    assert loaded["schema_version"] == "1"
    assert set(loaded["before"].keys()) == set(prev.keys())


def test_hkcu_diff_tuple_change_detection() -> None:
    assert hkcu_proxy_core_tuple(_snap(0, None)) != hkcu_proxy_core_tuple(_snap(1, None))
