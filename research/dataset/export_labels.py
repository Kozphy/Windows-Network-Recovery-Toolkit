"""Export research labels from canonical dataset v1."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from experiments.dataset import load_cases, repo_root
from research.dataset.schema import ResearchSample
from research.taxonomy import load_taxonomy

DEFAULT_LABELS = Path(__file__).resolve().parent / "labels.csv"


def _primary_failure_id(incident_class: str) -> str:
    tax = load_taxonomy()
    ids = tax.ids_for_incident_class(incident_class)
    if not ids:
        raise ValueError(f"no taxonomy mapping for incident class {incident_class!r}")
    return ids[0]


def _features_from_case(case_notes: str, failure_family: str) -> dict[str, object]:
    """Coarse anonymized features — no hostnames, users, or secrets."""
    return {
        "failure_family": failure_family,
        "has_notes": bool(case_notes.strip()),
        "feature_schema": "coarse_v1",
    }


def cases_to_samples() -> list[ResearchSample]:
    samples: list[ResearchSample] = []
    for case in load_cases():
        failure_id = _primary_failure_id(case.expected_incident_class)
        tax_cls = load_taxonomy().get(failure_id)
        compound = bool(tax_cls.compound) if tax_cls else False
        repairable = case.expected_remediation_posture not in {"BLOCK", "NONE"}
        if case.expected_remediation_posture == "NONE":
            repairable = False
        samples.append(
            ResearchSample(
                sample_id=case.case_id,
                scenario_id=case.case_id,
                os_version_category="unspecified_fixture",
                evidence_features=_features_from_case(case.notes, case.failure_family),
                ground_truth_failure=failure_id,
                ground_truth_incident_class=case.expected_incident_class,
                severity="ambiguous" if case.ambiguity_allowed else "labeled",
                compound_failure=compound,
                expected_action=case.expected_remediation_posture,
                repairable=repairable,
                provenance=case.provenance_category,
                generation_seed=None,
                split=case.split if case.split in {"development", "held_out"} else "development",
                limitations=list(case.limitations),
            )
        )
    return samples


def write_labels_csv(path: Path | None = None) -> Path:
    out = path or DEFAULT_LABELS
    out.parent.mkdir(parents=True, exist_ok=True)
    samples = cases_to_samples()
    fieldnames = list(ResearchSample.model_fields.keys())
    with out.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for sample in samples:
            row = sample.model_dump()
            row["evidence_features"] = json.dumps(row["evidence_features"], sort_keys=True)
            row["limitations"] = json.dumps(row["limitations"])
            writer.writerow(row)
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Export research labels.csv from dataset v1")
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_LABELS,
        help="Output CSV path",
    )
    args = parser.parse_args(argv)
    path = write_labels_csv(args.out)
    print(
        json.dumps(
            {
                "status": "ok",
                "path": str(path.relative_to(repo_root())),
                "rows": len(cases_to_samples()),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
