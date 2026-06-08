from __future__ import annotations

from platform_core.reasoning_engine import observation, run_reasoning
from platform_core.reasoning_models import ProofResult
from platform_core.state_machine import (
    CANONICAL_STATES,
    event_category,
    map_scenario_state,
)


def _proxy_path_observations():
    return [
        observation("ping_ok"),
        observation("dns_ok"),
        observation("tcp443_ok"),
        observation("browser_https_failed"),
        observation("wininet_proxy_enabled"),
        observation("localhost_proxy_detected"),
        observation("proxy_bypass_succeeded"),
        observation("proxied_path_failed"),
    ]


def test_canonical_states_cover_platform_enum() -> None:
    assert set(CANONICAL_STATES) == {
        "NORMAL",
        "SUSPICIOUS",
        "DEGRADED",
        "BROKEN",
        "RECOVERING",
    }


def test_scenario_states_map_to_canonical_layer() -> None:
    assert map_scenario_state("healthy_browser_path") == "NORMAL"
    assert map_scenario_state("proxy_drift_detected") == "SUSPICIOUS"
    assert map_scenario_state("proxy_path_failure_confirmed") == "BROKEN"


def test_proxy_path_reaches_broken_canonical_state() -> None:
    run = run_reasoning(
        _proxy_path_observations(),
        proof_result=ProofResult(
            hypothesis="browser_proxy_path_regression",
            status="CONFIRMED",
            confidence=0.95,
        ),
        requested_action="restore_proxy",
    )
    assert run.canonical_state_path == [
        "NORMAL",
        "SUSPICIOUS",
        "DEGRADED",
        "BROKEN",
    ]
    assert run.canonical_state_transitions
    assert all(item["rule_id"] for item in run.canonical_state_transitions)


def test_events_expose_event_id_and_category() -> None:
    run = run_reasoning(_proxy_path_observations())
    for event in run.detected_events:
        assert event.event_id == event.id
        assert event.category == event_category(event.event_type)


def test_replay_preserves_canonical_path() -> None:
    from platform_core.reasoning_audit import replay_reasoning_record, to_audit_record

    run = run_reasoning(_proxy_path_observations(), requested_action="restore_proxy")
    replayed = replay_reasoning_record(to_audit_record(run))
    assert replayed.canonical_state_path == run.canonical_state_path
