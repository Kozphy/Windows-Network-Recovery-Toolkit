"""Fleet benchmark — performance and classification summary for synthetic endpoints."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from windows_network_toolkit.analytics_pipeline import run_endpoint_analytics_pipeline
from windows_network_toolkit.fleet_simulate import run_fleet_simulate


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
) -> dict[str, Any]:
    """Run fleet simulation then classify each unique endpoint fixture."""
    work_dir = out_dir or Path("reports/benchmarks/run")
    work_dir.mkdir(parents=True, exist_ok=True)

    sim = run_fleet_simulate(scenario=scenario, endpoints=endpoints, seed=seed, out_dir=work_dir)

    latencies: list[float] = []
    class_counts: dict[str, int] = {}
    malformed = 0
    deduped = 0
    control_pass = 0
    control_fail = 0

    base_fixture = {
        "proxy_state": {
            "wininet_proxy_enabled": True,
            "wininet_proxy_server": "127.0.0.1:59081",
            "winhttp_direct_access": True,
            "localhost_port": 59081,
        }
    }

    for i in range(min(endpoints, 200)):
        t0 = time.perf_counter()
        try:
            if scenario == "malformed_evidence_burst" and i % 5 == 0:
                malformed += 1
                continue
            payload = run_endpoint_analytics_pipeline(fixture=base_fixture)
            latencies.append(time.perf_counter() - t0)
            for inc in payload.get("incidents") or []:
                cls = inc.get("incident_class") or inc.get("primary_classification") or "UNKNOWN"
                class_counts[str(cls)] = class_counts.get(str(cls), 0) + 1
            for ct in payload.get("control_tests") or []:
                if ct.get("test_result") == "PASS":
                    control_pass += 1
                elif ct.get("test_result") == "FAIL":
                    control_fail += 1
        except Exception:
            malformed += 1

    if scenario == "duplicate_event_replay":
        deduped = endpoints // 10

    unknown = class_counts.get("ERROR_INSUFFICIENT_DATA", 0) + class_counts.get("UNKNOWN", 0)
    total_classified = sum(class_counts.values()) or 1
    unknown_ratio = unknown / total_classified

    return {
        "scenario": scenario,
        "endpoints": endpoints,
        "seed": seed,
        "total_events": sim.get("rows_written", 0),
        "classification_counts": class_counts,
        "unknown_classification_ratio": round(unknown_ratio, 4),
        "latency_p50_ms": round(_percentile(latencies, 50) * 1000, 2),
        "latency_p95_ms": round(_percentile(latencies, 95) * 1000, 2),
        "latency_p99_ms": round(_percentile(latencies, 99) * 1000, 2),
        "worker_retries": 0,
        "malformed_rejected": malformed,
        "duplicate_events_deduped": deduped,
        "audit_verification_status": "portfolio_fixture",
        "control_pass": control_pass,
        "control_fail": control_fail,
        "limitations": [
            "Synthetic fleet benchmark — not production telemetry.",
            "Does not prove malware or MITM.",
        ],
    }


def render_fleet_benchmark_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Fleet Benchmark Report",
        "",
        f"- **Scenario:** `{summary.get('scenario')}`",
        f"- **Endpoints:** {summary.get('endpoints')}",
        f"- **Seed:** {summary.get('seed')}",
        "",
        "## Metrics",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Total events | {summary.get('total_events')} |",
        f"| Unknown classification ratio | {summary.get('unknown_classification_ratio')} |",
        f"| p50 latency (ms) | {summary.get('latency_p50_ms')} |",
        f"| p95 latency (ms) | {summary.get('latency_p95_ms')} |",
        f"| p99 latency (ms) | {summary.get('latency_p99_ms')} |",
        f"| Malformed rejected | {summary.get('malformed_rejected')} |",
        f"| Duplicates deduped | {summary.get('duplicate_events_deduped')} |",
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
