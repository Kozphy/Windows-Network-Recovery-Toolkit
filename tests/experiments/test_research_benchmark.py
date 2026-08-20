"""Executable research-layer contracts."""

from __future__ import annotations

import copy
import csv
import json
from pathlib import Path

from experiments.baselines.common import (
    load_dataset,
    stable_digest,
    verify_dataset_manifest,
)
from experiments.baselines.full_platform import predict as predict_b3
from experiments.scripts.build_report import build_report
from experiments.scripts.compute_metrics import compute_metrics, load_jsonl
from experiments.scripts.run_ablations import run_ablations
from experiments.scripts.run_benchmark import run_benchmark

ROOT = Path(__file__).resolve().parents[2]
DATASET = ROOT / "tests" / "fixtures" / "research" / "v1"
DATASET_MANIFEST = ROOT / "experiments" / "manifest.json"
BENCHMARK_CONFIG = ROOT / "experiments" / "configs" / "benchmark-v1.json"
ABLATION_CONFIG = ROOT / "experiments" / "configs" / "ablations-v1.json"


def _csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def test_frozen_synthetic_dataset_matches_manifest() -> None:
    cases, paths = load_dataset(DATASET)
    manifest = verify_dataset_manifest(
        DATASET_MANIFEST,
        dataset_root=DATASET,
        paths=paths,
    )
    assert len(cases) == 12
    assert manifest["case_count"] == 12
    assert {case["split"] for case in cases} == {"development", "held_out", "adversarial"}
    assert all(case["synthetic"] is True for case in cases)


def test_b3_adapter_does_not_read_expected_label() -> None:
    cases, _ = load_dataset(DATASET, splits=["development"])
    original = cases[0]
    changed_expected = copy.deepcopy(original)
    changed_expected["expected"]["classification"] = "INTENTIONALLY_DIFFERENT"
    assert predict_b3(original) == predict_b3(changed_expected)
    assert predict_b3(original).limitations
    assert predict_b3(original).unsafe_action_proposed is False


def test_benchmark_replays_are_deterministic_and_read_only(tmp_path: Path) -> None:
    first = run_benchmark(BENCHMARK_CONFIG, out_dir=tmp_path / "first")
    second = run_benchmark(BENCHMARK_CONFIG, out_dir=tmp_path / "second")
    assert first["prediction_count"] == 48
    assert first["replay_mismatch_count"] == 0
    assert second["replay_mismatch_count"] == 0

    first_rows = load_jsonl(first["predictions"])
    second_rows = load_jsonl(second["predictions"])
    assert [row["deterministic_digest"] for row in first_rows] == [
        row["deterministic_digest"] for row in second_rows
    ]
    assert all(not row["unsafe_action_proposed"] for row in first_rows)
    assert all(row["limitations"] for row in first_rows)
    assert all("action_taken" not in row for row in first_rows)
    for row in first_rows:
        digest_fields = {
            key: value
            for key, value in row.items()
            if key not in {"runtime_ms", "deterministic_digest"}
        }
        assert row["deterministic_digest"] == stable_digest(digest_fields)


def test_metrics_and_report_are_derived_from_executable_runs(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    benchmark = run_benchmark(BENCHMARK_CONFIG, out_dir=raw_dir)
    ablation = run_ablations(ABLATION_CONFIG, out_dir=raw_dir)
    assert ablation["prediction_count"] == 84
    assert ablation["replay_mismatch_count"] == 0

    ablation_rows = load_jsonl(ablation["predictions"])
    removed_limits = [
        row for row in ablation_rows if row["ablation"] == "A4_without_limitations"
    ]
    removed_gate = [
        row for row in ablation_rows if row["ablation"] == "A5_without_policy_gate"
    ]
    assert removed_limits and all(not row["limitations"] for row in removed_limits)
    assert removed_gate and any(row["unsafe_action_proposed"] for row in removed_gate)
    assert all("action_taken" not in row for row in ablation_rows)
    for row in ablation_rows:
        digest_fields = {
            key: value
            for key, value in row.items()
            if key not in {"runtime_ms", "deterministic_digest"}
        }
        assert row["deterministic_digest"] == stable_digest(digest_fields)

    benchmark_dir = tmp_path / "benchmarks"
    paths = compute_metrics(
        benchmark["predictions"],
        ablation["predictions"],
        out_dir=benchmark_dir,
        benchmark_manifest=benchmark["run_manifest"],
        ablation_manifest=ablation["run_manifest"],
    )
    for path in paths.values():
        assert path.is_file()

    result_rows = _csv_rows(paths["results"])
    assert {row["model_or_baseline"] for row in result_rows} == {
        "B0_connectivity_only",
        "B1_flat_rules",
        "B2_single_signal",
        "B3_full_platform",
    }
    assert any(row["split"] == "held_out" for row in result_rows)
    assert all(int(row["replay_mismatch_count"]) == 0 for row in result_rows)

    report_path = build_report(
        paths["results"],
        paths["ablations"],
        benchmark["run_manifest"],
        out_path=benchmark_dir / "benchmark_report.md",
    )
    report = report_path.read_text(encoding="utf-8")
    manifest = json.loads(benchmark["run_manifest"].read_text(encoding="utf-8"))
    assert manifest["dataset"]["sha256"] in report
    assert "not production telemetry" in report
    assert "B3_full_platform" in report
