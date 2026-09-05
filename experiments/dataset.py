"""Benchmark case models and dataset loading."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, model_validator

_REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET_DIR = _REPO_ROOT / "benchmarks" / "dataset_v1"


class BenchmarkCaseV1(BaseModel):
    """Single research benchmark case (dataset v1)."""

    case_id: str
    split: str = "development"
    provenance_category: str
    scenario_name: str = ""
    input_fixture_path: str | None = None
    fixture: dict[str, Any] | None = None
    expected_incident_class: str
    expected_min_proof_tier: str
    expected_control_outcome: str = "ANY"
    expected_policy_posture: str
    expected_remediation_posture: str
    limitations: list[str] = Field(default_factory=list)
    failure_family: str = ""
    ambiguity_allowed: bool = False
    notes: str = ""

    @model_validator(mode="after")
    def _has_input(self) -> BenchmarkCaseV1:
        if not self.fixture and not self.input_fixture_path:
            raise ValueError(f"case {self.case_id} requires fixture or input_fixture_path")
        return self


class DatasetManifest(BaseModel):
    """Frozen dataset manifest with content hashes."""

    schema_version: str = "research_benchmark_dataset.v1"
    dataset_version: str = "v1"
    case_count: int = 0
    development_count: int = 0
    held_out_count: int = 0
    files: dict[str, str] = Field(default_factory=dict)
    research_question_ref: str = "RESEARCH.md#primary-research-question"


def repo_root() -> Path:
    return _REPO_ROOT


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def load_cases(
    dataset_dir: Path | None = None,
    *,
    split: str | None = None,
) -> list[BenchmarkCaseV1]:
    """Load benchmark cases from cases.jsonl."""
    root = dataset_dir or DEFAULT_DATASET_DIR
    cases_path = root / "cases.jsonl"
    cases: list[BenchmarkCaseV1] = []
    for line in cases_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        case = BenchmarkCaseV1.model_validate(json.loads(line))
        if split is None or case.split == split:
            cases.append(case)
    return cases


def load_fixture(case: BenchmarkCaseV1, *, root: Path | None = None) -> dict[str, Any]:
    """Resolve inline or file-backed fixture for a case."""
    if case.fixture is not None:
        return case.fixture
    base = root or repo_root()
    path = base / str(case.input_fixture_path)
    return json.loads(path.read_text(encoding="utf-8"))


def build_manifest(dataset_dir: Path | None = None) -> DatasetManifest:
    """Build or refresh manifest with file hashes."""
    root = dataset_dir or DEFAULT_DATASET_DIR
    cases = load_cases(root)
    files = {
        "cases.jsonl": sha256_file(root / "cases.jsonl"),
        "label_schema.json": sha256_file(root / "label_schema.json"),
        "provenance.md": sha256_file(root / "provenance.md"),
    }
    dev = sum(1 for c in cases if c.split == "development")
    held = sum(1 for c in cases if c.split == "held_out")
    return DatasetManifest(
        case_count=len(cases),
        development_count=dev,
        held_out_count=held,
        files=files,
    )


def write_manifest(dataset_dir: Path | None = None) -> DatasetManifest:
    root = dataset_dir or DEFAULT_DATASET_DIR
    manifest = build_manifest(root)
    out = root / "manifest.json"
    out.write_text(manifest.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return manifest


def validate_dataset(dataset_dir: Path | None = None) -> list[str]:
    """Validate dataset schema; return list of errors (empty if valid)."""
    root = dataset_dir or DEFAULT_DATASET_DIR
    errors: list[str] = []
    schema_path = root / "label_schema.json"
    if not schema_path.is_file():
        errors.append("missing label_schema.json")
    cases_path = root / "cases.jsonl"
    if not cases_path.is_file():
        errors.append("missing cases.jsonl")
        return errors
    seen: set[str] = set()
    for idx, line in enumerate(cases_path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            case = BenchmarkCaseV1.model_validate(json.loads(line))
        except Exception as exc:  # noqa: BLE001 — validation report
            errors.append(f"line {idx}: {exc}")
            continue
        if case.case_id in seen:
            errors.append(f"duplicate case_id: {case.case_id}")
        seen.add(case.case_id)
        if case.input_fixture_path:
            fp = repo_root() / case.input_fixture_path
            if not fp.is_file():
                errors.append(f"{case.case_id}: missing fixture {case.input_fixture_path}")
    return errors
