from __future__ import annotations

from windows_network_toolkit.concurrency_benchmark import run_concurrency_benchmark


def test_concurrency_benchmark_accounts_for_all_tasks():
    result = run_concurrency_benchmark(tasks=8, workers=2)
    assert result["tasks"] == 8
    assert result["completed"] == 8
    assert result["failures"] == 0
    assert result["completed"] + result["failures"] == result["tasks"]
    assert result["throughput_tasks_per_s"] >= 0.0


def test_concurrency_benchmark_failure_injection_is_visible():
    result = run_concurrency_benchmark(tasks=10, workers=4, inject_failure_every=5)
    assert result["completed"] == 8
    assert result["failures"] == 2
    assert result["failure_ratio"] == 0.2


def test_concurrency_benchmark_rejects_invalid_inputs():
    import pytest

    with pytest.raises(ValueError):
        run_concurrency_benchmark(tasks=0)
    with pytest.raises(ValueError):
        run_concurrency_benchmark(workers=0)
    with pytest.raises(ValueError):
        run_concurrency_benchmark(inject_failure_every=-1)
