"""Tests for DiagnosticBaseline protocol adapters and B_ML."""

from __future__ import annotations

from pathlib import Path

from experiments.baselines.b_ml_bernoulli import (
    FEATURE_NAMES,
    extract_features,
    fit_b_ml_from_dataset,
)
from experiments.dataset import load_cases, load_fixture, repo_root
from experiments.runner import run_baseline, run_benchmark
from research.baselines import (
    DiagnosticBaseline,
    baseline_a_rules,
    baseline_b_heuristic,
    baseline_c_ml,
    baseline_d_proposed,
)


def test_adapters_satisfy_protocol() -> None:
    for factory in (baseline_a_rules, baseline_b_heuristic, baseline_d_proposed):
        obj = factory()
        assert isinstance(obj, DiagnosticBaseline)
        assert obj.metadata()["baseline"]


def test_feature_extraction_has_no_label_keys() -> None:
    cases = load_cases(split="development")
    fixture = load_fixture(cases[0], root=repo_root())
    feats = extract_features(fixture)
    assert len(feats) == len(FEATURE_NAMES)
    assert all(v in (0, 1) for v in feats)
    # Features must not encode the ground-truth class string as a dedicated feature name.
    assert "expected_incident_class" not in FEATURE_NAMES


def test_b_ml_trains_on_development_only_and_predicts() -> None:
    model = fit_b_ml_from_dataset(seed=42)
    meta = model.metadata()
    assert meta["train_size"] >= 10
    held = load_cases(split="held_out")
    assert held
    pred = model.predict(held[0], load_fixture(held[0], root=repo_root()))
    assert pred.baseline == "B_ML"
    assert pred.predicted_incident_class
    assert (
        "development" in " ".join(pred.limitations).lower()
        or "methodological" in " ".join(pred.limitations).lower()
    )


def test_b_ml_deterministic_for_seed() -> None:
    a = fit_b_ml_from_dataset(seed=42)
    b = fit_b_ml_from_dataset(seed=42)
    case = load_cases(split="held_out")[0]
    fixture = load_fixture(case, root=repo_root())
    assert (
        a.predict(case, fixture).predicted_incident_class
        == b.predict(case, fixture).predicted_incident_class
    )


def test_run_baseline_b_ml_returns_runtime() -> None:
    cases = load_cases()[:5]
    preds, runtime = run_baseline("B_ML", cases, root=repo_root(), seed=42)
    assert len(preds) == len(cases)
    assert runtime["wall_clock_ms"] >= 0
    assert runtime["baseline"] == "B_ML"


def test_smoke_benchmark_writes_runtime(tmp_path: Path) -> None:
    out = run_benchmark(
        output_dir=tmp_path / "run",
        smoke=True,
        seed=42,
        manifest_path=Path("experiments/configs/v1.json"),
    )
    assert (out / "runtime.csv").is_file()
    text = (out / "runtime.csv").read_text(encoding="utf-8")
    assert "B_ML" in text
    assert "wall_clock_ms" in text


def test_baseline_c_ml_adapter_fits() -> None:
    baseline = baseline_c_ml(seed=42)
    train = load_cases(split="development")[:8]
    fixtures = [load_fixture(c, root=repo_root()) for c in train]
    baseline.fit(train, fixtures, seed=42)
    pred = baseline.predict(train[0], fixtures[0])
    assert pred.baseline == "B_ML"
