"""Tests for experiment manifest contract."""

from pathlib import Path

from experiments.contract import load_manifest, validate_manifest_file


def test_default_manifest_loads() -> None:
    manifest = load_manifest()
    assert manifest.manifest_version == "experiment_manifest.v1"
    assert "B3" in manifest.baselines


def test_v1_manifest_validates() -> None:
    path = Path("experiments/manifests/v1.json")
    errors = validate_manifest_file(path)
    assert errors == []


def test_smoke_config_validates() -> None:
    path = Path("experiments/configs/v1.json")
    errors = validate_manifest_file(path)
    assert errors == []
