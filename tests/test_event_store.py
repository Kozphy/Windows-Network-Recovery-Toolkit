"""Unified event store append and replay timeline."""

from __future__ import annotations

from pathlib import Path

from platform_core.event_store import (
    append_decision,
    append_event,
    record_live_diagnosis_run,
    replay_timeline,
)


def test_record_live_diagnosis_writes_events_and_decisions(tmp_path: Path) -> None:
    record_live_diagnosis_run(
        tmp_path,
        run_id="run-abc",
        observations={"ping_ok": True},
        hypothesis_decisions=[
            {
                "decision": "PREVIEW",
                "reason_codes": ["HIGH_CONFIDENCE_UNPROVEN"],
                "blocked_actions": ["process_kill"],
                "proof_status": "UNPROVEN",
                "hypothesis": "fixture",
                "confidence": 0.9,
            }
        ],
    )
    tl = replay_timeline(tmp_path, "run-abc")
    assert len(tl["events"]) == 1
    assert tl["decision"]["decision"] == "PREVIEW"
    assert "HIGH_CONFIDENCE_UNPROVEN" in tl["decision"]["reason_codes"]


def test_append_only_grows_file(tmp_path: Path) -> None:
    append_event(tmp_path, run_id="r1", event_type="test")
    append_decision(tmp_path, run_id="r1", decision="BLOCK", reason_codes=["DESTRUCTIVE_ACTION_BLOCKED"])
    path = tmp_path / "logs" / "events.jsonl"
    assert path.read_text(encoding="utf-8").count("\n") >= 1
