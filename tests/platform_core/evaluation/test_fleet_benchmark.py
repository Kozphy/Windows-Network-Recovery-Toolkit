"""Fleet benchmark tests."""

from __future__ import annotations

import pytest

from windows_network_toolkit.benchmark_quality import (
    BenchmarkThresholds,
    capture_environment_manifest,
    evaluate_benchmark_regression,
)
from windows_network_toolkit.fleet_benchmark import run_fleet_benchmark


def test_fleet_benchmark_runs(tmp_path):
    summary = run_fleet_benchmark(
        scenario="mixed_proxy_failures",
        endpoints=10,
        seed=1,
        out_dir=tmp_path,
    )
    assert summary["benchmark_schema_version"] == "fleet-benchmark.v2"
    assert summary["endpoints"] == 10
    assert summary["simulated_endpoints"] == 10
    assert summary["measured_endpoints"] == 10
    assert summary["attempted_analytics"] == 10
    assert summary["completed_measurements"] == 10
    assert summary["execution_failures"] == 0
    assert summary["execution_failure_ratio"] == 0.0
    assert summary["environment"]["python_version"]
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


def test_failure_injection_is_counted_separately(tmp_path):
    summary = run_fleet_benchmark(
        scenario="mixed_proxy_failures",
        endpoints=10,
        seed=4,
        out_dir=tmp_path,
        inject_failure_every=3,
    )
    assert summary["measured_endpoints"] == 10
    assert summary["injected_failures"] == 3
    assert summary["execution_failures"] == 3
    assert summary["completed_measurements"] == 7
    assert summary["execution_failure_ratio"] == pytest.approx(0.3)


def test_environment_manifest_avoids_host_identity():
    manifest = capture_environment_manifest()
    assert manifest["python_version"]
    assert "hostname" not in manifest
    assert "username" not in manifest
    assert "environment" not in manifest


def test_regression_guard_passes_and_fails_explicitly():
    summary = {
        "measured_endpoints": 100,
        "execution_failures": 1,
        "latency_p95_ms": 12.0,
        "latency_p99_ms": 18.0,
        "analytics_throughput_eps": 500.0,
        "unknown_classification_ratio": 0.01,
    }
    passing = evaluate_benchmark_regression(
        summary,
        BenchmarkThresholds(
            max_p95_ms=15.0,
            max_p99_ms=20.0,
            min_throughput_eps=400.0,
            max_unknown_ratio=0.02,
            max_execution_failure_ratio=0.02,
        ),
    )
    assert passing["status"] == "PASS"
    assert passing["failed_checks"] == 0

    failing = evaluate_benchmark_regression(
        summary,
        BenchmarkThresholds(max_p95_ms=10.0, max_execution_failure_ratio=0.0),
    )
    assert failing["status"] == "FAIL"
    assert failing["failed_checks"] == 2


def test_fleet_benchmark_rejects_invalid_sizes(tmp_path):
    with pytest.raises(ValueError, match="endpoints"):
        run_fleet_benchmark(endpoints=0, out_dir=tmp_path)
    with pytest.raises(ValueError, match="measurement_cap"):
        run_fleet_benchmark(endpoints=1, measurement_cap=0, out_dir=tmp_path)
    with pytest.raises(ValueError, match="inject_failure_every"):
        run_fleet_benchmark(endpoints=1, inject_failure_every=0, out_dir=tmp_path)
