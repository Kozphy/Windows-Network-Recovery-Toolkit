from __future__ import annotations

from pathlib import Path

from platform_core.outcome_learning import replay_outcomes


def test_replay_deterministic(outcomes_fixture_path: Path) -> None:
    result_a = replay_outcomes(outcomes_fixture_path)
    result_b = replay_outcomes(outcomes_fixture_path)
    assert result_a == result_b
    assert result_a.outcome_count == 5
    assert len(result_a.content_digest) == 64
    assert "decision_accuracy" in result_a.report_markdown


def test_replay_metrics_stable(outcomes_fixture_path: Path) -> None:
    result = replay_outcomes(outcomes_fixture_path)
    assert result.metrics.sample_count == 5
    assert result.metrics.decision_accuracy == 0.4
    assert result.metrics.decision_precision == 0.5
    assert result.metrics.decision_recall == 0.6667
