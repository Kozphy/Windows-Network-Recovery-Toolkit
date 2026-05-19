"""Tests for backend.engine.detect_anomaly continuous-growth window."""

from __future__ import annotations

from backend.engine import _is_strictly_increasing, detect_anomaly


def _metrics_series(values: list[int], *, field: str = "time_wait") -> list[dict]:
    """Build newest-first metric rows (index 0 is most recent DB sample)."""
    other = "established" if field == "time_wait" else "time_wait"
    return [{field: v, other: 0} for v in reversed(values)]


def test_strictly_increasing_checks_all_adjacent_pairs_including_first() -> None:
    """Six samples must yield five step-up checks (including first→second)."""
    series = [10, 20, 30, 40, 50, 60]
    assert _is_strictly_increasing(series) is True
    # Break only the first adjacent pair — should fail.
    assert _is_strictly_increasing([10, 5, 30, 40, 50, 60]) is False


def test_five_samples_is_not_enough_for_five_step_ups() -> None:
    """Five points only support four increases; require six points for five pairs."""
    assert _is_strictly_increasing([1, 2, 3, 4, 5]) is False


def test_continuous_growth_detects_five_step_trend() -> None:
    recent = _metrics_series([100, 200, 300, 400, 500])
    out = detect_anomaly(current_time_wait=600, current_established=0, recent_metrics=recent)
    assert out["signals"]["continuous_growth"] is True


def test_continuous_growth_false_when_first_pair_not_increasing() -> None:
    recent = _metrics_series([500, 400, 300, 200, 100])
    out = detect_anomaly(current_time_wait=600, current_established=0, recent_metrics=recent)
    assert out["signals"]["continuous_growth"] is False
