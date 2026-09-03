"""Tests for the reproducible proxy-risk research benchmark."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from src.platform_core.evaluation.research_benchmark import (
    CaseResult,
    _per_class_rows,
    build_report,
    dataset_digest,
    execute_benchmark,
    load_config,
    load_research_cases,
)

ROOT = Path(__file__).resolve().parents[3]
CONFIG = ROOT / "experiments" / "configs" / "proxy-risk-v1.json"
CASES = ROOT / "tests" / "fixtures" / "research" / "proxy_risk_v1"


def test_case_contract_has_stable_splits_and_unique_ids() -> None:
    cases = load_research_cases(CASES)
    assert len(cases) == 12
    assert {case.split for case in cases} == {"development", "held_out", "adversarial"}
    assert len({case.case_id for case in cases}) == len(cases)
    assert all(case.provenance for case in cases)
    assert all(case.limitations for case in cases)


def test_dataset_digest_is_order_independent() -> None:
    cases = load_research_cases(CASES)
    assert dataset_digest(cases) == dataset_digest(reversed(cases))


def test_duplicate_case_id_is_rejected(tmp_path: Path) -> None:
    source = CASES / "development" / "DEV-001.json"
    destination = tmp_path / "development"
    destination.mkdir()
    payload = source.read_text(encoding="utf-8")
    (destination / "one.json").write_text(payload, encoding="utf-8")
    (destination / "two.json").write_text(payload, encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate case_id"):
        load_research_cases(tmp_path)


def test_split_directory_drift_is_rejected(tmp_path: Path) -> None:
    destination = tmp_path / "held_out"
    destination.mkdir()
    payload = (CASES / "development" / "DEV-001.json").read_text(encoding="utf-8")
    (destination / "case.json").write_text(payload, encoding="utf-8")
    with pytest.raises(ValueError, match="declares split"):
        load_research_cases(tmp_path)


def test_execute_benchmark_is_offline_and_replay_stable(tmp_path: Path) -> None:
    config = load_config(CONFIG, repo_root=ROOT)
    revision = "a" * 40
    manifest = execute_benchmark(CONFIG, tmp_path, repo_root=ROOT, code_revision=revision)
    rows = json.loads((tmp_path / "case_results.json").read_text(encoding="utf-8"))
    assert len(rows) == 12 * (len(config.baselines) + len(config.ablations))
    assert manifest["dataset"]["case_count"] == 12
    assert manifest["git_commit"] == revision
    assert manifest["dataset"]["sha256"] == dataset_digest(load_research_cases(CASES))
    assert all(row["replay_mismatch"] is False for row in rows)
    assert all(row["limitations"] for row in rows)


def test_report_regenerates_metrics_and_preserves_failures(tmp_path: Path) -> None:
    results = tmp_path / "results"
    output = tmp_path / "benchmarks"
    execute_benchmark(CONFIG, results, repo_root=ROOT)
    artifacts = build_report(results, output)
    assert all(path.is_file() for path in artifacts.values())

    with (output / "results.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    full = next(
        row
        for row in rows
        if row["split"] == "all" and row["model_or_baseline"] == "B3_FULL_PLATFORM"
    )
    flat = next(
        row
        for row in rows
        if row["split"] == "all" and row["model_or_baseline"] == "B1_FLAT_RULES"
    )
    assert int(full["case_count"]) == 12
    assert float(full["accuracy"]) == 1.0
    assert float(full["accuracy"]) > float(flat["accuracy"])
    assert int(full["replay_mismatch_count"]) == 0
    assert "B1_FLAT_RULES" in (output / "failure_analysis.md").read_text(encoding="utf-8")
    with (output / "ablations.csv").open(encoding="utf-8", newline="") as handle:
        ablations = list(csv.DictReader(handle))
    assert {row["ablation"] for row in ablations} == {
        "A1_NO_LISTENER",
        "A2_NO_PATH_HEALTH",
        "A3_NO_WINHTTP_CONTRAST",
        "A4_NO_TIMELINE",
    }
    assert all(float(row["delta_macro_f1_vs_full"]) <= 0 for row in ablations)


def test_report_rejects_tampered_raw_results(tmp_path: Path) -> None:
    execute_benchmark(CONFIG, tmp_path, repo_root=ROOT)
    raw = tmp_path / "case_results.json"
    raw.write_text(raw.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="digest"):
        build_report(tmp_path, tmp_path / "report")


def test_per_class_metric_math() -> None:
    base = {
        "benchmark_version": "test",
        "split": "held_out",
        "baseline": "B0_CONNECTIVITY",
        "expected_policy": "OBSERVE",
        "predicted_policy": "OBSERVE",
        "expected_min_tier": "T0",
        "proof_tier": "T0",
        "classification_supported": True,
        "policy_match": True,
        "abstained": False,
        "unsafe_action_proposed": False,
        "ambiguity_allowed": False,
        "limitations": ["test"],
        "runtime_ms": 0.0,
        "digest": "digest",
        "replay_mismatch": False,
    }
    rows = [
        CaseResult(
            **base,
            case_id="one",
            expected_class="A",
            predicted_class="A",
            classification_match=True,
        ),
        CaseResult(
            **base,
            case_id="two",
            expected_class="B",
            predicted_class="A",
            classification_match=False,
        ),
    ]
    metrics = _per_class_rows(
        rows,
        benchmark_version="test",
        split="held_out",
        baseline="B0_CONNECTIVITY",
    )
    a = next(row for row in metrics if row["class"] == "A")
    b = next(row for row in metrics if row["class"] == "B")
    assert a["precision"] == 0.5
    assert a["recall"] == 1.0
    assert b["precision"] == 0.0
    assert b["recall"] == 0.0
