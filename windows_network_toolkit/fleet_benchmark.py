"""Fleet benchmark — performance and classification summary for synthetic endpoints.

The benchmark intentionally distinguishes *requested/simulated* fleet size from the
number of endpoint pipelines actually timed. It also captures a privacy-safe execution
manifest and accounts for injected/real execution failures separately from malformed
fixture rejection.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from windows_network_toolkit.analytics_pipeline import run_endpoint_analytics_pipeline
from windows_network_toolkit.benchmark_quality import capture_environment_manifest
from windows_network_toolkit.fleet_simulate import run_fleet_simulate


DEFAULT_MEASUREMENT_CAP = 200


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = int(len(ordered) * pct / 100)
    return ordered[min(idx, len(ordered) - 1)]


def run_fleet_benchmark(
    *,
    scenario: str = "mixed_proxy_failures",
    endpoints: int = 100,
    seed: int = 42,
    out_dir: Path | None = None,
    measurement_cap: int = DEFAULT_MEASUREMENT_CAP,
    inject_failure_every: int | None = None,
) -> dict[str, Any]:
    """Run synthetic fleet generation and time endpoint analytics work.

    ``endpoints`` controls simulated scale. ``measurement_cap`` controls measured
    endpoint executions. ``inject_failure_every`` is a deterministic test hook: when
    set to N, every Nth measured execution fails before analytics runs. It exists for
    failure-accounting tests and demos, not for production fault injection.
    """
    if endpoints < 1:
        raise ValueError("endpoints must be >= 1")
    if measurement_cap < 1:
        raise ValueError("measurement_cap must be >= 1")
    if inject_failure_every is not None and inject_failure_every < 1:
        raise ValueError("inject_failure_every must be >= 1 when configured")

    work_dir = out_dir or Path("reports/benchmarks/run")
    work_dir.mkdir(parents=True, exist_ok=True)

    environment = capture_environment_manifest()
    wall_start = time.perf_counter()
    sim = run_fleet_simulate(scenario=scenario, endpoints=endpoints, seed=seed, out_dir=work_dir)

    latencies: list[float] = []
    class_counts: dict[str, int] = {}
    malformed = 0
    execution_failures = 0
    injected_failures = 0
    control_pass = 0
    control_fail = 0
    measured_endpoints = min(endpoints, measurement_cap)

    base_fixture = {
        "proxy_state": {
            "wininet_proxy_enabled": True,
            "wininet_proxy_server": "127.0.0.1:59081",
            "winhttp_direct_access": True,
            "localhost_port": 59081,
        }
    }

    analytics_start = time.perf_counter()
    completed_measurements = 0
    for i in range(measured_endpoints):
        t0 = time.perf_counter()
        try:
            if scenario == "malformed_evidence_burst" and i % 5 == 0:
                malformed += 1
                continue
            if inject_failure_every is not None and (i + 1) % inject_failure_every == 0:
                injected_failures += 1
                raise RuntimeError("deterministic benchmark failure injection")

            payload = run_endpoint_analytics_pipeline(fixture=base_fixture)
            elapsed = time.perf_counter() - t0
            latencies.append(elapsed)
            completed_measurements += 1
            for inc in payload.get("incidents") or []:
                cls = inc.get("incident_class") or inc.get("primary_classification") or "UNKNOWN"
                class_counts[str(cls)] = class_counts.get(str(cls), 0) + 1
            for ct in payload.get("control_tests") or []:
                if ct.get("test_result") == "PASS":
                    control_pass += 1
                elif ct.get("test_result") == "FAIL":
                    control_fail += 1
        except Exception:
            execution_failures += 1

    analytics_elapsed = time.perf_counter() - analytics_start
    wall_elapsed = time.perf_counter() - wall_start

    unknown = class_counts.get("ERROR_INSUFFICIENT_DATA", 0) + class_counts.get("UNKNOWN", 0)
    total_classified = sum(class_counts.values()) or 1
    unknown_ratio = unknown / total_classified
    throughput = completed_measurements / analytics_elapsed if analytics_elapsed > 0 else 0.0
    attempted_analytics = measured_endpoints - malformed
    failure_ratio = execution_failures / attempted_analytics if attempted_analytics > 0 else 0.0

    duplicate_pressure_expected = scenario == "duplicate_event_replay"

    return {
        "benchmark_schema_version": "fleet-benchmark.v2",
        "scenario": scenario,
        "requested_endpoints": endpoints,
        "endpoints": endpoints,
        "simulated_endpoints": endpoints,
        "measured_endpoints": measured_endpoints,
        "attempted_analytics": attempted_analytics,
        "completed_measurements": completed_measurements,
        "measurement_cap": measurement_cap,
        "seed": seed,
        "environment": environment,
        "total_events": sim.get("rows_written", 0),
        "classification_counts": class_counts,
        "unknown_classification_ratio": round(unknown_ratio, 4),
        "latency_p50_ms": round(_percentile(latencies, 50) * 1000, 2),
        "latency_p95_ms": round(_percentile(latencies, 95) * 1000, 2),
        "latency_p99_ms": round(_percentile(latencies, 99) * 1000, 2),
        "analytics_throughput_eps": round(throughput, 2),
        "analytics_elapsed_ms": round(analytics_elapsed * 1000, 2),
        "benchmark_wall_clock_ms": round(wall_elapsed * 1000, 2),
        "execution_failures": execution_failures,
        "execution_failure_ratio": round(failure_ratio, 4),
        "injected_failures": injected_failures,
        "failure_injection_every": inject_failure_every,
        "worker_retries": 0,
        "malformed_rejected": malformed,
        "duplicate_events_deduped": 0,
        "duplicate_events_deduped_measured": False,
        "duplicate_pressure_expected": duplicate_pressure_expected,
        "audit_verification_status": "portfolio_fixture",
        "control_pass": control_pass,
        "control_fail": control_fail,
        "limitations": [
            "Synthetic fleet benchmark — not production telemetry or an SLA claim.",
            f"Latency/throughput are measured over at most {measurement_cap} endpoint analytics executions; simulated fleet size may be larger.",
            "Duplicate pressure can be generated, but a production ingest deduplication rate is not measured by this harness.",
            "Single-process local timing is hardware- and environment-dependent; compare runs only with captured environment metadata.",
            "Failure injection is deterministic test instrumentation, not distributed chaos engineering.",
            "Does not prove malware or MITM.",
        ],
    }


def render_fleet_benchmark_markdown(summary: dict[str, Any]) -> str:
    env = summary.get("environment") or {}
    lines = [
        "# Fleet Benchmark Report",
        "",
        f"- **Schema:** `{summary.get('benchmark_schema_version', 'fleet-benchmark.v1')}`",
        f"- **Scenario:** `{summary.get('scenario')}`",
        f"- **Requested / simulated endpoints:** {summary.get('simulated_endpoints', summary.get('endpoints'))}",
        f"- **Measured endpoint executions:** {summary.get('measured_endpoints', summary.get('endpoints'))}",
        f"- **Completed measurements:** {summary.get('completed_measurements', summary.get('measured_endpoints', summary.get('endpoints')))}",
        f"- **Seed:** {summary.get('seed')}",
        "",
        "## Execution environment",
        "",
        "| Field | Value |",
        "|-------|-------|",
        f"| Python | {env.get('python_implementation', 'unknown')} {env.get('python_version', 'unknown')} |",
        f"| OS | {env.get('platform_system', 'unknown')} {env.get('platform_release', '')} |",
        f"| Machine | {env.get('machine', 'unknown')} |",
        f"| CPU count | {env.get('cpu_count', 'unknown')} |",
        f"| Commit | `{env.get('git_commit', 'unknown')}` |",
        f"| CI | {env.get('ci', False)} |",
        "",
        "## Metrics",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Total simulated events | {summary.get('total_events')} |",
        f"| Unknown classification ratio | {summary.get('unknown_classification_ratio')} |",
        f"| p50 endpoint pipeline latency (ms) | {summary.get('latency_p50_ms')} |",
        f"| p95 endpoint pipeline latency (ms) | {summary.get('latency_p95_ms')} |",
        f"| p99 endpoint pipeline latency (ms) | {summary.get('latency_p99_ms')} |",
        f"| Analytics throughput (endpoint executions/s) | {summary.get('analytics_throughput_eps', 'n/a')} |",
        f"| Analytics elapsed (ms) | {summary.get('analytics_elapsed_ms', 'n/a')} |",
        f"| Benchmark wall clock (ms) | {summary.get('benchmark_wall_clock_ms', 'n/a')} |",
        f"| Execution failures | {summary.get('execution_failures', 0)} |",
        f"| Execution failure ratio | {summary.get('execution_failure_ratio', 0.0)} |",
        f"| Injected failures | {summary.get('injected_failures', 0)} |",
        f"| Malformed rejected | {summary.get('malformed_rejected')} |",
        f"| Duplicates deduped | {summary.get('duplicate_events_deduped')} (measured={summary.get('duplicate_events_deduped_measured', False)}) |",
        f"| Control PASS | {summary.get('control_pass')} |",
        f"| Control FAIL | {summary.get('control_fail')} |",
        "",
        "## Classification counts",
        "",
    ]
    for cls, count in sorted((summary.get("classification_counts") or {}).items()):
        lines.append(f"- `{cls}`: {count}")
    lines.extend(["", "## Limitations", ""])
    for lim in summary.get("limitations") or []:
        lines.append(f"- {lim}")
    return "\n".join(lines) + "\n"
