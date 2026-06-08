"""Prometheus metrics for the Decision Intelligence API.

In-process counters/gauges rendered by :func:`render_prometheus_lines` and merged
into the platform ``GET /metrics`` handler.

Thread safety:
    All mutations are guarded by a module lock.

Audit Notes:
    ``decision_failures`` increments on outcome POST where ``success=false``.
    ``decision_accuracy`` is refreshed from outcome-learning replay results.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager

_lock = threading.Lock()

_counters: dict[str, float] = {
    "events_total": 0.0,
    "decisions_total": 0.0,
    "decision_failures": 0.0,
}

_gauges: dict[str, float] = {
    "decision_accuracy": 0.0,
    "decision_latency_seconds": 0.0,
}

_latency_sum_seconds: float = 0.0
_latency_count: int = 0

_METRIC_HELP: dict[str, str] = {
    "events_total": "Total decision-intelligence events recorded via API.",
    "decisions_total": "Total decisions recorded via API.",
    "decision_failures": "Outcomes where success=false (ground-truth failure).",
    "decision_accuracy": "Latest batch decision accuracy from outcome learning (0-1).",
    "decision_latency_seconds": "Mean API handler latency for decision-intelligence routes.",
}


def inc_event() -> None:
    with _lock:
        _counters["events_total"] += 1.0


def inc_decision() -> None:
    with _lock:
        _counters["decisions_total"] += 1.0


def inc_decision_failure() -> None:
    with _lock:
        _counters["decision_failures"] += 1.0


def set_decision_accuracy(value: float) -> None:
    with _lock:
        _gauges["decision_accuracy"] = max(0.0, min(1.0, float(value)))


def record_latency(seconds: float) -> None:
    global _latency_sum_seconds, _latency_count
    with _lock:
        _latency_sum_seconds += max(0.0, seconds)
        _latency_count += 1
        if _latency_count > 0:
            _gauges["decision_latency_seconds"] = _latency_sum_seconds / _latency_count


@contextmanager
def observe_handler_latency() -> Iterator[None]:
    start = time.perf_counter()
    try:
        yield
    finally:
        record_latency(time.perf_counter() - start)


def refresh_accuracy_from_learning(accuracy: float) -> None:
    set_decision_accuracy(accuracy)


def render_prometheus_lines() -> str:
    with _lock:
        counters = dict(_counters)
        gauges = dict(_gauges)
    lines: list[str] = []
    for name, value in sorted(counters.items()):
        lines.append(f"# HELP {name} {_METRIC_HELP.get(name, name)}")
        lines.append(f"# TYPE {name} counter")
        lines.append(f"{name} {value}")
    for name, value in sorted(gauges.items()):
        lines.append(f"# HELP {name} {_METRIC_HELP.get(name, name)}")
        lines.append(f"# TYPE {name} gauge")
        lines.append(f"{name} {value}")
    return "\n".join(lines) + "\n"


def reset_for_tests() -> None:
    global _latency_sum_seconds, _latency_count
    with _lock:
        for key in _counters:
            _counters[key] = 0.0
        _gauges["decision_accuracy"] = 0.0
        _gauges["decision_latency_seconds"] = 0.0
        _latency_sum_seconds = 0.0
        _latency_count = 0
