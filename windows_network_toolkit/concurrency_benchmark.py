"""Local concurrency benchmark for endpoint analytics.

This measures only concurrent local execution of the deterministic analytics pipeline.
It does not claim broker, database, network, or production fleet capacity.
"""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from windows_network_toolkit.analytics_pipeline import run_endpoint_analytics_pipeline


def run_concurrency_benchmark(
    *,
    tasks: int = 100,
    workers: int = 4,
    inject_failure_every: int = 0,
) -> dict[str, Any]:
    if tasks < 1:
        raise ValueError("tasks must be >= 1")
    if workers < 1:
        raise ValueError("workers must be >= 1")
    if inject_failure_every < 0:
        raise ValueError("inject_failure_every must be >= 0")

    fixture = {
        "proxy_state": {
            "wininet_proxy_enabled": True,
            "wininet_proxy_server": "127.0.0.1:59081",
            "winhttp_direct_access": True,
            "localhost_port": 59081,
        }
    }

    def one(index: int) -> float:
        started = time.perf_counter()
        if inject_failure_every and (index + 1) % inject_failure_every == 0:
            raise RuntimeError("deterministic injected concurrency failure")
        run_endpoint_analytics_pipeline(fixture=fixture)
        return time.perf_counter() - started

    started = time.perf_counter()
    latencies: list[float] = []
    failures = 0
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(one, i) for i in range(tasks)]
        for future in as_completed(futures):
            try:
                latencies.append(future.result())
            except Exception:
                failures += 1
    elapsed = time.perf_counter() - started

    ordered = sorted(latencies)

    def percentile(pct: float) -> float:
        if not ordered:
            return 0.0
        idx = min(int(len(ordered) * pct / 100), len(ordered) - 1)
        return ordered[idx]

    completed = len(latencies)
    return {
        "schema_version": "concurrency-benchmark.v1",
        "tasks": tasks,
        "workers": workers,
        "completed": completed,
        "failures": failures,
        "failure_ratio": round(failures / tasks, 4),
        "elapsed_ms": round(elapsed * 1000, 2),
        "throughput_tasks_per_s": round(completed / elapsed, 2) if elapsed else 0.0,
        "latency_p50_ms": round(percentile(50) * 1000, 2),
        "latency_p95_ms": round(percentile(95) * 1000, 2),
        "latency_p99_ms": round(percentile(99) * 1000, 2),
        "limitations": [
            "Local ThreadPoolExecutor benchmark only; not production fleet capacity.",
            "No broker, network, database, persistence, or multi-host scheduling is measured.",
            "Python runtime and host hardware materially affect results.",
        ],
    }
