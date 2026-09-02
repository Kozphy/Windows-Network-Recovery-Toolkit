"""Frozen experimental contract models and manifest loading."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

_REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = _REPO_ROOT / "experiments" / "manifests" / "v1.json"


class OutputSubdirs(BaseModel):
    raw: str = "experiments/raw_results"
    processed: str = "experiments/processed_results"


class ExperimentManifest(BaseModel):
    """Frozen experiment configuration (manifest v1)."""

    manifest_version: str = "experiment_manifest.v1"
    experiment_id: str
    description: str = ""
    dataset_version: str = "v1"
    dataset_path: str = "benchmarks/dataset_v1"
    baselines: list[str] = Field(default_factory=lambda: ["B0", "B1", "B2", "B3"])
    random_seed: int = 42
    bootstrap_iterations: int = 1000
    confidence_level: float = 0.95
    smoke_case_limit: int | None = None
    output_subdirs: OutputSubdirs = Field(default_factory=OutputSubdirs)
    research_question_ref: str = "RESEARCH.md"


class ExperimentRunRecord(BaseModel):
    """Per-scenario run record (experimental contract output row)."""

    experiment_id: str
    timestamp_utc: str
    git_commit_sha: str
    dataset_version: str
    manifest_version: str
    baseline: str
    configuration: str
    random_seed: int
    scenario_id: str
    ground_truth: str
    prediction: str
    proof_tier: str = ""
    policy_posture: str = ""
    remediation_posture: str = ""
    confidence_score: float | None = None
    recovery_action: str = "none"
    recovery_success: str = "not_applicable"
    detection_latency_ms: float | None = None
    recovery_latency_ms: float | None = None
    unsupported_decision: bool = False
    abstained: bool = False
    unsafe_action_proposed: bool = False
    failure_category: str = ""
    split: str = "development"
    limitations_count: int = 0


def load_manifest(path: Path | None = None) -> ExperimentManifest:
    """Load and validate experiment manifest JSON."""
    manifest_path = path or DEFAULT_MANIFEST
    if not manifest_path.is_absolute():
        manifest_path = _REPO_ROOT / manifest_path
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    return ExperimentManifest.model_validate(data)


def validate_manifest_file(path: Path) -> list[str]:
    """Return validation errors for a manifest file."""
    errors: list[str] = []
    if not path.is_file():
        return [f"missing manifest: {path}"]
    try:
        manifest = load_manifest(path)
    except Exception as exc:  # noqa: BLE001
        return [str(exc)]
    for baseline in manifest.baselines:
        if baseline not in {"B0", "B1", "B2", "B3"}:
            errors.append(f"unknown baseline: {baseline}")
    ds = _REPO_ROOT / manifest.dataset_path
    if not ds.is_dir():
        errors.append(f"dataset path missing: {manifest.dataset_path}")
    return errors


def manifest_digest(manifest: ExperimentManifest) -> dict[str, Any]:
    return manifest.model_dump()
