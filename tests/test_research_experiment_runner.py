from __future__ import annotations

import json
from pathlib import Path

from research import experiment_runner


def test_experiment_separates_simulated_from_measured_scale(monkeypatch, tmp_path: Path) -> None:
    def fake_fleet(**kwargs):
        assert kwargs["endpoints"] == 10_000
        assert kwargs["measurement_cap"] == 25
        return {
            "scenario": kwargs["scenario"],
            "simulated_endpoints": kwargs["endpoints"],
            "measured_endpoints": kwargs["measurement_cap"],
            "completed_measurements": kwargs["measurement_cap"],
            "seed": kwargs["seed"],
            "total_events": 10_000,
            "classification_counts": {"DEAD_PROXY_CONFIG": 25},
            "unknown_classification_ratio": 0.0,
            "malformed_rejected": 0,
            "control_pass": 25,
            "control_fail": 0,
        }

    def fake_concurrency(**kwargs):
        return {
            "tasks": kwargs["tasks"],
            "workers": kwargs["workers"],
            "completed": kwargs["tasks"],
            "failures": 0,
            "failure_ratio": 0.0,
            "latency_p95_ms": 1.0,
        }

    monkeypatch.setattr(experiment_runner, "run_fleet_benchmark", fake_fleet)
    monkeypatch.setattr(experiment_runner, "run_concurrency_benchmark", fake_concurrency)

    config = experiment_runner.ExperimentConfig(
        simulated_endpoints=10_000,
        measurement_cap=25,
        concurrency_tasks=50,
        concurrency_workers=4,
        seed=42,
    )
    result = experiment_runner.run_experiment(config, tmp_path)

    assert result["fleet"]["simulated_endpoints"] == 10_000
    assert result["fleet"]["measured_endpoints"] == 25
    assert result["claim_boundary"]["production_capacity_claimed"] is False
    assert result["claim_boundary"]["sla_claimed"] is False
    assert result["claim_boundary"]["simulated_scale_is_not_measured_scale"] is True

    stored = json.loads((tmp_path / "result.json").read_text(encoding="utf-8"))
    manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    assert stored["reproducibility_digest"] == manifest["reproducibility_digest"]
    assert len(manifest["result_sha256"]) == 64


def test_reproducibility_digest_ignores_timing_and_environment_noise() -> None:
    base = {
        "config": {"seed": 42},
        "fleet": {
            "scenario": "mixed_proxy_failures",
            "simulated_endpoints": 100,
            "measured_endpoints": 10,
            "completed_measurements": 10,
            "seed": 42,
            "total_events": 100,
            "classification_counts": {"A": 10},
            "unknown_classification_ratio": 0.0,
            "malformed_rejected": 0,
            "control_pass": 10,
            "control_fail": 0,
            "latency_p99_ms": 1.0,
        },
        "concurrency": {
            "tasks": 10,
            "workers": 2,
            "completed": 10,
            "failures": 0,
            "failure_ratio": 0.0,
            "latency_p99_ms": 2.0,
        },
        "environment": {"platform": "host-a"},
        "generated_at": "time-a",
    }
    noisy = json.loads(json.dumps(base))
    noisy["fleet"]["latency_p99_ms"] = 999.0
    noisy["concurrency"]["latency_p99_ms"] = 888.0
    noisy["environment"] = {"platform": "host-b"}
    noisy["generated_at"] = "time-b"

    first = experiment_runner._sha256(experiment_runner._reproducibility_projection(base))
    second = experiment_runner._sha256(experiment_runner._reproducibility_projection(noisy))
    assert first == second


def test_invalid_experiment_config_is_rejected() -> None:
    config = experiment_runner.ExperimentConfig(simulated_endpoints=0)
    try:
        config.validate()
    except ValueError as exc:
        assert "simulated_endpoints" in str(exc)
    else:
        raise AssertionError("invalid config must be rejected")
