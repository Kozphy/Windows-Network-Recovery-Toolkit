"""Export dataset v1 scenarios view and sync with benchmarks."""

from __future__ import annotations

import json
from pathlib import Path

from experiments.dataset import (
    DEFAULT_DATASET_DIR,
    BenchmarkCaseV1,
    load_cases,
    repo_root,
    write_manifest,
)

DATASETS_V1 = repo_root() / "datasets" / "v1"


def case_to_scenario(case: BenchmarkCaseV1) -> dict:
    """Map benchmark case to scenario schema (research fault corpus view)."""
    return {
        "scenario_id": case.case_id,
        "fault_family": case.failure_family or "unknown",
        "fault_type": case.expected_incident_class,
        "severity": "ambiguous" if case.ambiguity_allowed else "labeled",
        "preconditions": case.provenance_category,
        "injected_fault": case.input_fixture_path or "inline_fixture",
        "observable_signals": ["proxy_state", "health_inject", "path_health"],
        "ground_truth_class": case.expected_incident_class,
        "expected_supported_evidence": case.expected_min_proof_tier,
        "expected_safe_action": case.expected_remediation_posture,
        "expected_recovery_state": "preview_only",
        "tags": [case.split, case.provenance_category],
        "synthetic": True,
        "limitations": case.limitations,
    }


def export_scenarios_jsonl(
    *,
    dataset_dir: Path | None = None,
    out_dir: Path | None = None,
) -> Path:
    """Write datasets/v1/scenarios.jsonl from benchmark cases."""
    cases = load_cases(dataset_dir)
    target = out_dir or DATASETS_V1
    target.mkdir(parents=True, exist_ok=True)
    out_path = target / "scenarios.jsonl"
    with out_path.open("w", encoding="utf-8") as fh:
        for case in cases:
            fh.write(json.dumps(case_to_scenario(case), sort_keys=True) + "\n")
    return out_path


def sync_datasets_v1(*, dataset_dir: Path | None = None) -> None:
    """Refresh datasets/v1 manifest and scenarios from benchmarks/dataset_v1."""
    ds_benchmark = dataset_dir or DEFAULT_DATASET_DIR
    manifest = write_manifest(ds_benchmark)
    target = DATASETS_V1
    target.mkdir(parents=True, exist_ok=True)

    export_scenarios_jsonl(dataset_dir=ds_benchmark, out_dir=target)

    schema_src = ds_benchmark / "label_schema.json"
    if schema_src.is_file():
        (target / "schema.json").write_text(
            schema_src.read_text(encoding="utf-8"), encoding="utf-8"
        )

    readme = target / "README.md"
    if not readme.is_file():
        readme.write_text(
            "# Dataset v1 (fault scenario corpus)\n\n"
            "Mirrors `benchmarks/dataset_v1/` for research reviewers.\n\n"
            "- `scenarios.jsonl` — exported scenario view\n"
            "- `manifest.json` — content hashes\n"
            "- `schema.json` — label schema\n\n"
            "Regenerate: `python -m experiments.run_all` or `scripts/reproduce.ps1`\n",
            encoding="utf-8",
        )

    manifest_out = {
        "schema_version": "research_scenario_corpus.v1",
        "dataset_version": "v1",
        "source": "benchmarks/dataset_v1",
        "case_count": manifest.case_count,
        "files": manifest.files,
    }
    (target / "manifest.json").write_text(
        json.dumps(manifest_out, indent=2) + "\n", encoding="utf-8"
    )
