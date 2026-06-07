"""Tests for reliability metrics derived from JSONL."""

from __future__ import annotations

import json
from pathlib import Path

from platform_core.reliability_metrics import compute_reliability_metrics


def test_reliability_metrics_from_fixture_jsonl(tmp_path: Path) -> None:
    signals = tmp_path / "platform_signals.jsonl"
    rows = [
        {"kind": "browser_path_ok", "occurred_at": "2026-01-15T12:00:00+00:00", "detected_at": "2026-01-15T12:00:05+00:00"},
        {"kind": "browser_path_failed"},
        {"kind": "proxy_registry_change"},
        {"kind": "incident_opened"},
        {"kind": "incident_false_positive"},
        {"kind": "remediation_stickiness_ok"},
        {"kind": "remediation_stickiness_failed"},
    ]
    with signals.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")

    metrics = compute_reliability_metrics(data_root=tmp_path)
    assert metrics.browser_path_success_rate == 0.5
    assert metrics.proxy_drift_events_per_day == 1.0
    assert metrics.false_positive_rate == 0.5
    assert metrics.remediation_stickiness_rate == 0.5
    assert metrics.mean_time_to_detect_seconds == 5.0
