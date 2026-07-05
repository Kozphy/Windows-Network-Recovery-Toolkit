"""Prometheus metrics for technology-risk pipeline."""

from __future__ import annotations

import threading

_lock = threading.Lock()
_counters: dict[str, float] = {}
_histogram_sum: dict[str, float] = {}
_histogram_count: dict[str, float] = {}
_gauges: dict[str, float] = {}

_METRICS = (
    "evidence_events_ingested_total",
    "incidents_classified_total",
    "policy_decisions_total",
    "audit_chain_append_total",
    "audit_chain_verification_failures_total",
    "worker_jobs_total",
    "worker_job_failures_total",
    "domain_events_appended_total",
    "mcp_tool_invocations_total",
)


def inc(name: str, amount: float = 1.0, labels: dict[str, str] | None = None) -> None:
    key = name if not labels else f"{name}{{{','.join(f'{k}={v!r}' for k,v in sorted(labels.items()))}}}"
    with _lock:
        _counters[key] = _counters.get(key, 0.0) + amount


def set_gauge(name: str, value: float) -> None:
    with _lock:
        _gauges[name] = value


def inc_classification(classification: str) -> None:
    inc("incidents_classified_total", labels={"classification": classification})


def observe_classification_latency(seconds: float) -> None:
    with _lock:
        _histogram_sum["classification_latency_seconds"] = (
            _histogram_sum.get("classification_latency_seconds", 0.0) + seconds
        )
        _histogram_count["classification_latency_seconds"] = (
            _histogram_count.get("classification_latency_seconds", 0.0) + 1.0
        )


def render_trisk_prometheus_lines() -> list[str]:
    lines: list[str] = []
    with _lock:
        for k, v in sorted(_counters.items()):
            lines.append(f"{k} {v}")
        for k, v in sorted(_gauges.items()):
            lines.append(f"{k} {v}")
        if _histogram_count.get("classification_latency_seconds"):
            lines.append(
                f"classification_latency_seconds_sum {_histogram_sum.get('classification_latency_seconds', 0.0)}"
            )
            lines.append(
                f"classification_latency_seconds_count {_histogram_count.get('classification_latency_seconds', 0.0)}"
            )
    return lines


def reset_trisk_metrics() -> None:
    with _lock:
        _counters.clear()
        _gauges.clear()
        _histogram_sum.clear()
        _histogram_count.clear()
