"""Bounded proxy incident loop: language, flip-flop, causality, soak."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

from src.proxy_guard.causality_labels import (
    LISTENER_CORRELATION,
    REGISTRY_WRITER_PROOF,
    attribution_mode_label,
    format_listener_correlation,
)
from src.proxy_guard.flip_flop import detect_active_reverter, iter_enable_transitions
from src.proxy_guard.human_report import format_proxy_guard_change, format_watch_report
from src.proxy_guard.operator_language import display_policy_decision
from src.proxy_guard.soak import run_remediation_soak


def test_allowed_maps_to_observe_no_rollback() -> None:
    assert display_policy_decision("allowed") == "observe_no_rollback"
    text = format_proxy_guard_change(
        {
            "schema_version": 2,
            "timestamp": "2026-05-16T09:40:31Z",
            "event": "proxy_guard_change",
            "before_snapshot": {"proxy_enable": 0, "proxy_server": "127.0.0.1:1"},
            "after_snapshot": {"proxy_enable": 1, "proxy_server": "127.0.0.1:1"},
            "attribution": {"mode": "best_effort_process_snapshot", "process": {"name": "node.exe", "pid": 1}},
            "policy_decision": {"decision": "allowed", "reason": "localhost_loopback_policy_allow"},
        }
    )
    assert "observe_no_rollback" in text
    assert "does NOT mean the proxy state is safe" in text


def test_three_toggles_within_30_minutes_active_reverter() -> None:
    base = datetime(2026, 5, 16, 9, 0, 0, tzinfo=timezone.utc)
    rows = []
    for i, (old, new) in enumerate([(1, 0), (0, 1), (1, 0)]):
        rows.append(
            {
                "schema_version": 2,
                "timestamp": (base + timedelta(minutes=i * 5)).isoformat(),
                "before_snapshot": {"proxy_enable": old},
                "after_snapshot": {"proxy_enable": new},
            }
        )
    ref = base + timedelta(minutes=20)
    incident = detect_active_reverter(rows, reference_utc=ref)
    assert incident is not None
    assert incident.incident_class == "ACTIVE_REVERTER"
    report = format_watch_report(rows, all_records_for_flip_flop=rows)
    assert "ACTIVE_REVERTER" in report


def test_two_toggles_only_no_active_reverter() -> None:
    base = datetime(2026, 5, 16, 9, 0, 0, tzinfo=timezone.utc)
    rows = [
        {
            "timestamp": base.isoformat(),
            "before_snapshot": {"proxy_enable": 1},
            "after_snapshot": {"proxy_enable": 0},
        },
        {
            "timestamp": (base + timedelta(minutes=5)).isoformat(),
            "before_snapshot": {"proxy_enable": 0},
            "after_snapshot": {"proxy_enable": 1},
        },
    ]
    assert detect_active_reverter(rows, reference_utc=base + timedelta(minutes=20)) is None


def test_listener_correlation_is_not_registry_writer_proof() -> None:
    assert attribution_mode_label("best_effort_process_snapshot") == LISTENER_CORRELATION
    lines = format_listener_correlation(process_name="node.exe", pid=42)
    blob = "\n".join(lines)
    assert REGISTRY_WRITER_PROOF in blob
    assert "does not prove registry writer" in blob
    assert "caused" not in blob.lower()


def test_soak_stable_when_proxy_stays_disabled() -> None:
    reg = MagicMock(proxy_enable=0, proxy_server=None, auto_config_url=None, auto_detect=0, proxy_override=None)

    def _read(**_kwargs):
        return reg

    import src.proxy_guard.soak as soak_mod

    original = soak_mod.read_proxy_registry
    soak_mod.read_proxy_registry = _read  # type: ignore[assignment]
    try:
        result = run_remediation_soak(
            soak_minutes=0.01,
            poll_seconds=0.001,
            run=MagicMock(),
            sleep_fn=lambda _: None,
        )
    finally:
        soak_mod.read_proxy_registry = original

    assert result.status == "STABLE"


def test_soak_remediation_not_sticky_on_reenable() -> None:
    calls = {"n": 0}

    def _read(**_kwargs):
        calls["n"] += 1
        en = 0 if calls["n"] == 1 else 1
        reg = MagicMock(proxy_enable=en, proxy_server=None, auto_config_url=None, auto_detect=0, proxy_override=None)
        return reg

    import src.proxy_guard.soak as soak_mod

    original = soak_mod.read_proxy_registry
    soak_mod.read_proxy_registry = _read  # type: ignore[assignment]
    try:
        result = run_remediation_soak(
            soak_minutes=1.0,
            poll_seconds=0.001,
            run=MagicMock(),
            sleep_fn=lambda _: None,
        )
    finally:
        soak_mod.read_proxy_registry = original

    assert result.status == "REMEDIATION_NOT_STICKY"
    assert "active reverter" in result.detail.lower()


def test_v1_normalized_transitions() -> None:
    rows = [
        {
            "schema_version": 1,
            "event": "proxy_state_change",
            "timestamp_utc": "2026-05-16T09:00:00Z",
            "old_enable": 0,
            "new_enable": 1,
        },
    ]
    transitions = iter_enable_transitions(rows)
    assert len(transitions) == 1
    assert transitions[0][1:] == (0, 1)
