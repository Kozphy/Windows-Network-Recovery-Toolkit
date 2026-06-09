"""Replay determinism contract (root-level suite for CI discovery)."""

from __future__ import annotations

import json
from pathlib import Path

from platform_core.replay.runner import accumulate_replay_counters, run_replay, summarize_inline


def test_replay_identical_events_yield_identical_summary() -> None:
    events = [
        {
            "schema_version": "1",
            "event_id": "det-1",
            "signals": {
                "remediation_action": "inspect_proxy",
                "simulated_operator_role": "admin",
            },
            "policy_decision": {
                "execute_allowed": False,
                "preview_allowed": True,
                "reason_codes": ["ok"],
                "required_role": "admin",
                "risk_tier": "read_only",
            },
        }
    ]
    assert summarize_inline(events) == summarize_inline(events)


def test_replay_jsonl_fixture_offline(tmp_path: Path) -> None:
    path = tmp_path / "events.jsonl"
    path.write_text(
        json.dumps(
            {
                "schema_version": "1",
                "signals": {"remediation_action": "reset_dns", "simulated_operator_role": "operator"},
            }
        ),
        encoding="utf-8",
    )
    summary = run_replay(path)
    assert summary.total_events == 1
    assert summary.parse_errors == 0


def test_demo_fixture_replay_pipeline_stable() -> None:
    from pathlib import Path

    from platform_core.demo_replay import build_replay_events, replay_summary_from_events

    repo = Path(__file__).resolve().parents[1]
    path = repo / "tests" / "fixtures" / "demo" / "final_causation_browser_path_failure.json"
    blob = json.loads(path.read_text(encoding="utf-8"))
    events = build_replay_events(blob)
    assert replay_summary_from_events(events) == replay_summary_from_events(events)


def test_replay_detects_stale_embedded_execute_allow() -> None:
    events = [
        {
            "schema_version": "1",
            "signals": {"remediation_action": "process_kill_forbidden", "simulated_operator_role": "admin"},
            "policy_decision": {
                "execute_allowed": True,
                "preview_allowed": True,
                "reason_codes": ["stale"],
                "required_role": "admin",
                "risk_tier": "forbidden",
            },
        }
    ]
    summary = accumulate_replay_counters(events)
    assert summary.newly_blocked_execute >= 1
