"""Replay determinism and read-only guarantees."""

from __future__ import annotations

from pathlib import Path

from platform_core.policy import OperatorContext, evaluate
from platform_core.replay.runner import accumulate_replay_counters, run_replay, summarize_inline


def test_replay_inline_is_deterministic_for_identical_events() -> None:
    events = [
        {
            "schema_version": "1",
            "event_id": "replay-det-1",
            "event_type": "normalized.remediation_candidate",
            "severity": "low",
            "endpoint_id_hash": "a" * 32,
            "signals": {
                "remediation_action": "inspect_proxy",
                "simulated_operator_role": "admin",
                "simulated_surface": "api",
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
    first = summarize_inline(events)
    second = summarize_inline(events)
    assert first == second
    assert first.total_events == 1
    assert first.parse_errors == 0


def test_replay_runner_has_no_subprocess_dependency() -> None:
    """Replay re-evaluates stored policy only — no subprocess/spawn hooks in module."""

    import platform_core.replay.runner as runner_mod

    source = Path(runner_mod.__file__).read_text(encoding="utf-8")
    assert "subprocess" not in source
    assert "collect_features" not in source


def test_replay_fixture_jsonl_offline(tmp_path: Path) -> None:
    path = tmp_path / "events.jsonl"
    path.write_text(
        "\n".join(
            [
                '{"schema_version":"1","event_id":"e1","signals":{"remediation_action":"reset_dns","simulated_operator_role":"admin"}}',
                '{"schema_version":"1","event_id":"e2","signals":{"remediation_action":"process_kill_forbidden","simulated_operator_role":"admin"}}',
            ]
        ),
        encoding="utf-8",
    )
    summary = run_replay(path)
    assert summary.total_events == 2
    assert summary.parse_errors == 0


def test_high_confidence_forbidden_action_stays_blocked_in_replay() -> None:
    ctx = OperatorContext(role="admin", surface="api")
    gate = evaluate({"confidence": 1.0, "summary": "sure kill"}, "process_kill_forbidden", ctx)
    assert gate.execute_allowed is False

    events = [
        {
            "schema_version": "1",
            "event_id": "replay-kill-1",
            "signals": {
                "remediation_action": "process_kill_forbidden",
                "simulated_operator_role": "admin",
                "confidence": 1.0,
            },
            "policy_decision": {
                "execute_allowed": True,
                "preview_allowed": True,
                "reason_codes": ["stale_wrong"],
                "required_role": "admin",
                "risk_tier": "forbidden",
            },
        }
    ]
    summary = accumulate_replay_counters(events)
    assert summary.changed_decisions >= 1
    assert summary.newly_blocked_execute >= 1


def test_replay_api_mode_is_read_only_label() -> None:
    """Platform replay preview endpoint advertises read-only mode."""
    from fastapi.testclient import TestClient

    from backend.main import app

    client = TestClient(
        app,
        headers={"X-Operator-Role": "admin", "X-Operator-Id": "replay-readonly"},
    )
    payload = {
        "events": [
            {
                "schema_version": "1",
                "event_id": "replay-api-ro",
                "signals": {
                    "remediation_action": "inspect_proxy",
                    "simulated_operator_role": "admin",
                },
            }
        ]
    }
    r = client.post("/platform/replay/preview", json=payload)
    assert r.status_code == 200
    assert r.json().get("replay_mode") == "read_only"
