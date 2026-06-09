"""Outcome store tests."""

from __future__ import annotations

from pathlib import Path

from src.platform_core.outcome.store import load_outcomes, record_outcome


def test_record_and_load(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    import src.platform_core.outcome.store as st

    monkeypatch.setattr(st, "_DEFAULT", tmp_path / "outcomes.jsonl")
    record_outcome(
        decision_id="d1",
        incident_id="i1",
        recommended_action="PREVIEW",
        policy_outcome="PREVIEW_ONLY",
        was_successful=True,
        time_to_resolution_seconds=120.0,
    )
    rows = load_outcomes(tmp_path / "outcomes.jsonl")
    assert len(rows) == 1
    assert rows[0].decision_id == "d1"
