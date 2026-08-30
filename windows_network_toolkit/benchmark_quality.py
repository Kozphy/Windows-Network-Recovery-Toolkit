"""Benchmark reproducibility and regression-quality helpers.

These helpers keep portfolio benchmarks honest: capture the execution environment,
separate hard failures from expected malformed inputs, and compare a current run
against explicit thresholds without pretending local synthetic timing is an SLA.
"""

from __future__ import annotations

import os
import platform
import sys
from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class BenchmarkThresholds:
    """Portable guardrails for comparing like-for-like benchmark runs."""

    max_p95_ms: float | None = None
    max_p99_ms: float | None = None
    min_throughput_eps: float | None = None
    max_unknown_ratio: float | None = None
    max_execution_failure_ratio: float | None = 0.0


def capture_environment_manifest() -> dict[str, Any]:
    """Return low-risk metadata needed to interpret a local benchmark run.

    Host names, usernames, environment variables, and network identifiers are
    intentionally excluded so reports can be committed without leaking workstation
    identity. Commit SHA may be supplied by CI through ``GITHUB_SHA``.
    """

    return {
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "platform_system": platform.system(),
        "platform_release": platform.release(),
        "machine": platform.machine(),
        "processor": platform.processor() or "unknown",
        "cpu_count": os.cpu_count(),
        "executable_bits": 64 if sys.maxsize > 2**32 else 32,
        "git_commit": os.getenv("GITHUB_SHA") or os.getenv("GIT_COMMIT") or "unknown",
        "ci": bool(os.getenv("CI")),
    }


def evaluate_benchmark_regression(
    summary: dict[str, Any],
    thresholds: BenchmarkThresholds,
) -> dict[str, Any]:
    """Evaluate explicit thresholds and return an auditable PASS/FAIL artifact.

    Thresholds are intentionally opt-in for latency and throughput because local
    hardware varies. CI can pin thresholds once runners and fixtures are stable.
    """

    checks: list[dict[str, Any]] = []

    def add_check(name: str, observed: float, operator: str, limit: float | None) -> None:
        if limit is None:
            checks.append(
                {
                    "name": name,
                    "status": "NOT_CONFIGURED",
                    "observed": observed,
                    "operator": operator,
                    "threshold": None,
                }
            )
            return
        passed = observed <= limit if operator == "<=" else observed >= limit
        checks.append(
            {
                "name": name,
                "status": "PASS" if passed else "FAIL",
                "observed": observed,
                "operator": operator,
                "threshold": limit,
            }
        )

    attempted = int(summary.get("measured_endpoints", 0) or 0)
    failures = int(summary.get("execution_failures", 0) or 0)
    failure_ratio = failures / attempted if attempted else 0.0

    add_check("latency_p95_ms", float(summary.get("latency_p95_ms", 0.0) or 0.0), "<=", thresholds.max_p95_ms)
    add_check("latency_p99_ms", float(summary.get("latency_p99_ms", 0.0) or 0.0), "<=", thresholds.max_p99_ms)
    add_check(
        "analytics_throughput_eps",
        float(summary.get("analytics_throughput_eps", 0.0) or 0.0),
        ">=",
        thresholds.min_throughput_eps,
    )
    add_check(
        "unknown_classification_ratio",
        float(summary.get("unknown_classification_ratio", 0.0) or 0.0),
        "<=",
        thresholds.max_unknown_ratio,
    )
    add_check("execution_failure_ratio", failure_ratio, "<=", thresholds.max_execution_failure_ratio)

    configured = [check for check in checks if check["status"] != "NOT_CONFIGURED"]
    failures_found = [check for check in configured if check["status"] == "FAIL"]
    status = "FAIL" if failures_found else ("PASS" if configured else "NOT_CONFIGURED")

    return {
        "status": status,
        "thresholds": asdict(thresholds),
        "checks": checks,
        "configured_checks": len(configured),
        "failed_checks": len(failures_found),
        "limitations": [
            "Regression thresholds are meaningful only for comparable fixtures and execution environments.",
            "Local synthetic benchmark thresholds are engineering guardrails, not production SLOs or SLAs.",
        ],
    }
