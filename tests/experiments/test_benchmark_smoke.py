"""Research benchmark smoke tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from experiments.dataset import validate_dataset, write_manifest
from experiments.runner import run_benchmark


@pytest.mark.parametrize("split", [None, "development"])
def test_dataset_validates(split: None | str) -> None:
    errors = validate_dataset()
    assert errors == [], errors


def test_manifest_writes_with_hashes() -> None:
    manifest = write_manifest()
    assert manifest.case_count >= 20
    assert "cases.jsonl" in manifest.files


def test_benchmark_smoke_deterministic() -> None:
    from tempfile import mkdtemp

    base = Path(mkdtemp(prefix="rb_det_"))
    out1 = run_benchmark(output_dir=base / "run1", smoke=True, seed=42)
    out2 = run_benchmark(output_dir=base / "run2", smoke=True, seed=42)
    preds1 = (out1 / "predictions.csv").read_text(encoding="utf-8")
    preds2 = (out2 / "predictions.csv").read_text(encoding="utf-8")
    assert preds1 == preds2


def test_benchmark_smoke_outputs() -> None:
    from tempfile import mkdtemp

    base = Path(mkdtemp(prefix="rb_out_"))
    out = run_benchmark(output_dir=base / "run", smoke=True, seed=42)
    for name in (
        "metadata.json",
        "predictions.csv",
        "metrics.csv",
        "reproducibility_metrics.csv",
        "bootstrap_ci.csv",
        "results.csv",
    ):
        assert (out / name).is_file(), name
    metadata = json.loads((out / "metadata.json").read_text(encoding="utf-8"))
    repro = metadata.get("reproducibility", {})
    assert repro.get("digest_agreement") is True
