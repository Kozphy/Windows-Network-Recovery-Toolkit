"""Executable research experiment orchestrator.

This module turns the repository's research protocol into machine-readable artifacts.
It deliberately separates simulated scale from measured execution and never converts
benchmark output into unsupported production/SLA claims.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from windows_network_toolkit.concurrency_benchmark import run_concurrency_benchmark
from windows_network_toolkit.fleet_benchmark import run_fleet_benchmark


SCHEMA_VERSION = "research-experiment.v1"


@dataclass(frozen=True)
class ExperimentConfig:
    scenario: str = "mixed_proxy_failures"
    simulated_endpoints: int = 10_000
    measurement_cap: int = 200
    concurrency_tasks: int = 1_000
    concurrency_workers: int = 8
    seed: int = 42

    def validate(self) -> None:
        if self.simulated_endpoints < 1:
            raise ValueError("simulated_endpoints must be >= 1")
        if self.measurement_cap < 1:
            raise ValueError("measurement_cap must be >= 1")
        if self.concurrency_tasks < 1:
            raise ValueError("concurrency_tasks must be >= 1")
        if self.concurrency_workers < 1:
            raise ValueError("concurrency_workers must be >= 1")


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _environment() -> dict[str, Any]:
    return {
        "python": sys.version.split()[0],
        "implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
    }


def _reproducibility_projection(result: dict[str, Any]) -> dict[str, Any]:
    """Keep deterministic fields only; wall-clock timings are intentionally excluded."""
    fleet = result["fleet"]
    concurrency = result["concurrency"]
    return {
        "config": result["config"],
        "fleet": {
            "scenario": fleet.get("scenario"),
            "simulated_endpoints": fleet.get("simulated_endpoints"),
            "measured_endpoints": fleet.get("measured_endpoints"),
            "completed_measurements": fleet.get("completed_measurements"),
            "seed": fleet.get("seed"),
            "total_events": fleet.get("total_events"),
            "classification_counts": fleet.get("classification_counts"),
            "unknown_classification_ratio": fleet.get("unknown_classification_ratio"),
            "malformed_rejected": fleet.get("malformed_rejected"),
            "control_pass": fleet.get("control_pass"),
            "control_fail": fleet.get("control_fail"),
        },
        "concurrency": {
            "tasks": concurrency.get("tasks"),
            "workers": concurrency.get("workers"),
            "completed": concurrency.get("completed"),
            "failures": concurrency.get("failures"),
            "failure_ratio": concurrency.get("failure_ratio"),
        },
    }


def run_experiment(config: ExperimentConfig, out_dir: Path) -> dict[str, Any]:
    config.validate()
    out_dir.mkdir(parents=True, exist_ok=True)

    fleet_dir = out_dir / "fleet"
    fleet = run_fleet_benchmark(
        scenario=config.scenario,
        endpoints=config.simulated_endpoints,
        seed=config.seed,
        out_dir=fleet_dir,
        measurement_cap=config.measurement_cap,
    )
    concurrency = run_concurrency_benchmark(
        tasks=config.concurrency_tasks,
        workers=config.concurrency_workers,
    )

    result: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "config": asdict(config),
        "environment": _environment(),
        "fleet": fleet,
        "concurrency": concurrency,
        "claim_boundary": {
            "simulated_scale_is_not_measured_scale": True,
            "production_capacity_claimed": False,
            "sla_claimed": False,
            "autonomous_remediation_claimed": False,
        },
        "limitations": [
            "Synthetic/replay evidence is not production fleet telemetry.",
            "Local timing depends on host hardware, Python runtime, and background load.",
            "The benchmark does not measure a real broker, database, multi-host scheduler, or network path.",
            "A 10k simulated fleet does not imply 10k concurrently measured endpoint executions.",
        ],
    }
    result["reproducibility_digest"] = _sha256(_reproducibility_projection(result))

    (out_dir / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    manifest = {
        "schema_version": "research-manifest.v1",
        "result_sha256": hashlib.sha256((out_dir / "result.json").read_bytes()).hexdigest(),
        "reproducibility_digest": result["reproducibility_digest"],
        "config_sha256": _sha256(asdict(config)),
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run a reproducible research/scale experiment")
    parser.add_argument("--out-dir", type=Path, default=Path("experiments/results/latest"))
    parser.add_argument("--scenario", default="mixed_proxy_failures")
    parser.add_argument("--simulated-endpoints", type=int, default=10_000)
    parser.add_argument("--measurement-cap", type=int, default=200)
    parser.add_argument("--concurrency-tasks", type=int, default=1_000)
    parser.add_argument("--concurrency-workers", type=int, default=8)
    parser.add_argument("--seed", type=int, default=42)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    config = ExperimentConfig(
        scenario=args.scenario,
        simulated_endpoints=args.simulated_endpoints,
        measurement_cap=args.measurement_cap,
        concurrency_tasks=args.concurrency_tasks,
        concurrency_workers=args.concurrency_workers,
        seed=args.seed,
    )
    result = run_experiment(config, args.out_dir)
    print(json.dumps({
        "schema_version": result["schema_version"],
        "reproducibility_digest": result["reproducibility_digest"],
        "simulated_endpoints": result["fleet"].get("simulated_endpoints"),
        "measured_endpoints": result["fleet"].get("measured_endpoints"),
        "production_capacity_claimed": False,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
