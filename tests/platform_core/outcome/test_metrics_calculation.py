"""Metrics calculation tests."""

from __future__ import annotations

from pathlib import Path

from src.platform_core.outcome.metrics import compute_metrics
from src.platform_core.outcome.store import record_outcome


def test_metrics_with_data(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    import src.platform_core.outcome.store as st

    p = tmp_path / "outcomes.jsonl"
    monkeypatch.setattr(st, "_DEFAULT", p)
    record_outcome(
        decision_id="d1",
        incident_id="i1",
        recommended_action="A",
        policy_outcome="PREVIEW_ONLY",
        was_successful=True,
        time_to_resolution_seconds=100.0,
    )
    record_outcome(
        decision_id="d2",
        incident_id="i2",
        recommended_action="B",
        policy_outcome="BLOCK",
        was_false_positive=True,
        was_blocked_by_policy=True,
    )
    m = compute_metrics(baseline_mttr_seconds=500.0)
    assert m["sample_size"] == 2
    assert m["decision_accuracy"] == 0.5
    assert m["false_positive_rate"] == 0.5
