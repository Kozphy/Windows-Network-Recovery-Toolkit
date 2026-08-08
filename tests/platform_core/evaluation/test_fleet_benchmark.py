"""Fleet benchmark tests."""

from __future__ import annotations

import pytest

from windows_network_toolkit.fleet_benchmark import run_fleet_benchmark


def test_fleet_benchmark_runs(tmp_path):
    summary = run_fleet_benchmark(
        scenario="mixed_proxy_failures",
        endpoints=10,
        seed=1,
        out_dir=tmp_path,
    )
    assert summary["endpoints"] == 10
    assert summary["simulated_endpoints"] == 10
    assert summary["measured_endpoints"] == 10
    assert summary["completed_measurements"] == 10
    assert "classification_counts" in summary
    assert summary["unknown_classification_ratio"] >= 0.0
    assert summary["latency_p95_ms"] >= 0.0
    assert summary["analytics_throughput_eps"] >= 0.0
    assert summary["duplicate_events_deduped_measured"] is False


def test_fleet_benchmark_reports_measurement_cap(tmp_path):
    summary = run_fleet_benchmark(
        scenario="mixed_proxy_failures",
        endpoints=25,
        seed=2,
        out_dir=tmp_path,
        measurement_cap=7,
    )
    assert summary["simulated_endpoints"] == 25
    assert summary["measured_endpoints"] == 7
    assert summary["completed_measurements"] == 7
    assert summary["measurement_cap"] == 7
    assert any("at most 7" in item for item in summary["limitations"])


def test_duplicate_scenario_does_not_fabricate_dedupe_count(tmp_path):
    summary = run_fleet_benchmark(
        scenario="duplicate_event_replay",
        endpoints=10,
        seed=3,
        out_dir=tmp_path,
    )
    assert summary["duplicate_pressure_expected"] is True
    assert summary["duplicate_events_deduped"] == 0
    assert summary["duplicate_events_deduped_measured"] is False


def test_fleet_benchmark_rejects_invalid_sizes(tmp_path):
    with pytest.raises(ValueError, match="endpoints"):
        run_fleet_benchmark(endpoints=0, out_dir=tmp_path)
    with pytest.raises(ValueError, match="measurement_cap"):
        run_fleet_benchmark(endpoints=1, measurement_cap=0, out_dir=tmp_path)
