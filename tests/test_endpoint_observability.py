"""Tests for JSONL-derived endpoint Prometheus gauges."""

from __future__ import annotations

import json
from pathlib import Path

from platform_core.endpoint_observability import compute_endpoint_prometheus_gauges


def test_diagnosis_duration_seconds_from_signal_timestamps(tmp_path: Path) -> None:
    signals = tmp_path / "platform_signals.jsonl"
    signals.write_text(
        json.dumps(
            {
                "kind": "proxy_change",
                "occurred_at": "2026-06-04T10:00:00+00:00",
                "detected_at": "2026-06-04T10:00:05+00:00",
            }
        )
        + "\n"
        + json.dumps(
            {
                "kind": "proxy_change",
                "occurred_at": "2026-06-04T10:01:00+00:00",
                "detected_at": "2026-06-04T10:01:03+00:00",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (tmp_path / "failure_events.jsonl").write_text("", encoding="utf-8")
    (tmp_path / "audit.jsonl").write_text("", encoding="utf-8")
    (tmp_path / "remediation_previews.jsonl").write_text("", encoding="utf-8")
    (tmp_path / "endpoints.jsonl").write_text("", encoding="utf-8")

    gauges = compute_endpoint_prometheus_gauges(data_root=tmp_path)
    assert gauges["diagnosis_duration_seconds"] == 4.0
    assert gauges["proxy_drift_incidents_total"] == 2.0
