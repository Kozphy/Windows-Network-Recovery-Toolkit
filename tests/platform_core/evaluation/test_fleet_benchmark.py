"""Fleet benchmark tests."""

from __future__ import annotations

from windows_network_toolkit.fleet_benchmark import run_fleet_benchmark


def test_fleet_benchmark_runs(tmp_path):
    summary = run_fleet_benchmark(
        scenario="mixed_proxy_failures",
        endpoints=10,
        seed=1,
        out_dir=tmp_path,
    )
    assert summary["endpoints"] == 10
    assert "classification_counts" in summary
    assert summary["unknown_classification_ratio"] >= 0.0
