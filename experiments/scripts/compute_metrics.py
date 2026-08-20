"""Derive benchmark CSV and JSON metrics from executable raw prediction rows."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.baselines.common import ABSTENTION_CLASSIFICATIONS, stable_digest  # noqa: E402
from experiments.scripts._shared import generated_at_utc, write_json  # noqa: E402

RESULT_FIELDS = [
    "benchmark_version",
    "split",
    "model_or_baseline",
    "case_count",
    "accuracy",
    "macro_precision",
    "macro_recall",
    "macro_f1",
    "unsupported_classification_rate",
    "abstention_rate",
    "explicit_limitation_rate",
    "proof_minimum_met_rate",
    "policy_match_rate",
    "unsafe_action_proposal_rate",
    "replay_mismatch_count",
    "mean_runtime_ms",
    "git_commit",
    "dataset_digest",
]

CONFUSION_FIELDS = [
    "benchmark_version",
    "split",
    "model_or_baseline",
    "expected_class",
    "predicted_class",
    "count",
]

ABLATION_FIELDS = [
    "benchmark_version",
    "split",
    "ablation",
    "case_count",
    "accuracy",
    "macro_f1",
    "unsupported_classification_rate",
    "explicit_limitation_rate",
    "proof_minimum_met_rate",
    "policy_match_rate",
    "unsafe_action_proposal_rate",
    "replay_mismatch_count",
    "delta_macro_f1_vs_full",
    "delta_unsupported_rate_vs_full",
    "notes",
    "git_commit",
    "dataset_digest",
]

_ABLATION_NOTES = {
    "full": "Reference B3 fixture-only platform adapter.",
    "A1_without_proof_tiers": "Proof tier output forced to T0; classification is unchanged.",
    "A2_without_listener_evidence": "Listener/process observations removed before classification.",
    "A3_without_tls_path_evidence": "Direct/proxy path results removed before classification.",
    "A4_without_limitations": "Explicit limitations removed to measure evidence-quality loss.",
    "A5_without_policy_gate": (
        "Counterfactual proposals only; no remediation is executed by the benchmark."
    ),
    "A7_without_cross_signal_aggregation": "Uses the B1 first-match flat-rule adapter.",
}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    """Load non-empty JSONL records and reject non-object rows."""
    rows: list[dict[str, Any]] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        row = json.loads(line)
        if not isinstance(row, dict):
            raise ValueError(f"{path}:{number} must contain a JSON object")
        rows.append(row)
    if not rows:
        raise ValueError(f"raw prediction file is empty: {path}")
    return rows


def _validate_raw_rows(
    rows: list[dict[str, Any]],
    *,
    expected_schema: str,
    group_key: str,
) -> None:
    """Reject mixed, duplicated, or digest-invalid raw prediction inputs."""
    identity_fields = ("benchmark_version", "dataset_digest", "git_commit")
    first_identity = tuple(rows[0].get(field) for field in identity_fields)
    seen: set[tuple[str, str, str]] = set()
    for row in rows:
        if row.get("schema_version") != expected_schema:
            raise ValueError(f"unexpected raw row schema: {row.get('schema_version')!r}")
        identity = tuple(row.get(field) for field in identity_fields)
        if identity != first_identity:
            raise ValueError("raw prediction rows mix benchmark, dataset, or git identities")
        key = (str(row.get("split")), str(row.get(group_key)), str(row.get("case_id")))
        if key in seen:
            raise ValueError(f"duplicate raw prediction row: {key}")
        seen.add(key)
        digest_fields = {
            field: value
            for field, value in row.items()
            if field not in {"runtime_ms", "deterministic_digest"}
        }
        if row.get("deterministic_digest") != stable_digest(digest_fields):
            raise ValueError(f"deterministic digest mismatch for {row.get('case_id')}")


def _validate_run_manifest(
    rows: list[dict[str, Any]],
    manifest: dict[str, Any],
    *,
    run_kind: str,
) -> None:
    """Verify that a run manifest identifies the supplied raw rows."""
    if manifest.get("schema_version") != "research_run_manifest.v1":
        raise ValueError("unsupported run manifest schema")
    if manifest.get("run_kind") != run_kind:
        raise ValueError(f"expected {run_kind} run manifest")
    first = rows[0]
    checks = {
        "prediction_count": len(rows),
        "benchmark_version": first["benchmark_version"],
        "git_commit": first["git_commit"],
        "replay_mismatch_count": sum(1 for row in rows if row["replay_mismatch"]),
    }
    for field, expected in checks.items():
        if manifest.get(field) != expected:
            raise ValueError(f"run manifest {field} mismatch")
    if (manifest.get("dataset") or {}).get("sha256") != first["dataset_digest"]:
        raise ValueError("run manifest dataset digest mismatch")


def _rate(rows: list[dict[str, Any]], predicate) -> float:
    return sum(1 for row in rows if predicate(row)) / len(rows)


def _macro_scores(rows: list[dict[str, Any]]) -> tuple[float, float, float]:
    labels = sorted({str(row["expected_class"]) for row in rows})
    precisions: list[float] = []
    recalls: list[float] = []
    f1s: list[float] = []
    for label in labels:
        true_positive = sum(
            1
            for row in rows
            if row["expected_class"] == label and row["predicted_class"] == label
        )
        false_positive = sum(
            1
            for row in rows
            if row["expected_class"] != label and row["predicted_class"] == label
        )
        false_negative = sum(
            1
            for row in rows
            if row["expected_class"] == label and row["predicted_class"] != label
        )
        precision = true_positive / (true_positive + false_positive) if true_positive + false_positive else 0.0
        recall = true_positive / (true_positive + false_negative) if true_positive + false_negative else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        precisions.append(precision)
        recalls.append(recall)
        f1s.append(f1)
    return (
        sum(precisions) / len(precisions),
        sum(recalls) / len(recalls),
        sum(f1s) / len(f1s),
    )


def _metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    precision, recall, f1 = _macro_scores(rows)
    first = rows[0]
    return {
        "benchmark_version": first["benchmark_version"],
        "case_count": len(rows),
        "accuracy": round(_rate(rows, lambda row: bool(row["correct"])), 6),
        "macro_precision": round(precision, 6),
        "macro_recall": round(recall, 6),
        "macro_f1": round(f1, 6),
        "unsupported_classification_rate": round(
            _rate(rows, lambda row: not bool(row["classification_supported"])), 6
        ),
        "abstention_rate": round(
            _rate(rows, lambda row: row["predicted_class"] in ABSTENTION_CLASSIFICATIONS),
            6,
        ),
        "explicit_limitation_rate": round(
            _rate(rows, lambda row: bool(row["has_explicit_limitations"])), 6
        ),
        "proof_minimum_met_rate": round(
            _rate(rows, lambda row: bool(row["proof_tier_meets_minimum"])), 6
        ),
        "policy_match_rate": round(_rate(rows, lambda row: bool(row["policy_match"])), 6),
        "unsafe_action_proposal_rate": round(
            _rate(rows, lambda row: bool(row["unsafe_action_proposed"])), 6
        ),
        "replay_mismatch_count": sum(1 for row in rows if row["replay_mismatch"]),
        "mean_runtime_ms": round(
            sum(float(row["runtime_ms"]) for row in rows) / len(rows), 6
        ),
        "git_commit": first["git_commit"],
        "dataset_digest": first["dataset_digest"],
    }


def _group_with_all(
    rows: list[dict[str, Any]],
    *,
    group_key: str,
) -> dict[tuple[str, str], list[dict[str, Any]]]:
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        name = str(row[group_key])
        split = str(row["split"])
        groups[(split, name)].append(row)
        groups[("all", name)].append(row)
    return groups


def benchmark_metrics(
    rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Compute per-split/overall summaries and long-form confusion counts."""
    result_rows: list[dict[str, Any]] = []
    confusion_rows: list[dict[str, Any]] = []
    groups = _group_with_all(rows, group_key="model_or_baseline")
    for (split, model), group in sorted(groups.items()):
        result_rows.append({**_metrics(group), "split": split, "model_or_baseline": model})
        counts = Counter((row["expected_class"], row["predicted_class"]) for row in group)
        for (expected, predicted), count in sorted(counts.items()):
            confusion_rows.append(
                {
                    "benchmark_version": group[0]["benchmark_version"],
                    "split": split,
                    "model_or_baseline": model,
                    "expected_class": expected,
                    "predicted_class": predicted,
                    "count": count,
                }
            )
    return result_rows, confusion_rows


def ablation_metrics(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Compute ablation summaries and deltas against full B3 for the same split."""
    groups = _group_with_all(rows, group_key="ablation")
    base_by_split = {
        split: _metrics(group)
        for (split, name), group in groups.items()
        if name == "full"
    }
    if set(base_by_split) != {"development", "held_out", "adversarial", "all"}:
        raise ValueError("ablation rows must contain full results for every configured split")

    output: list[dict[str, Any]] = []
    for (split, name), group in sorted(groups.items()):
        metrics = _metrics(group)
        base = base_by_split[split]
        output.append(
            {
                "benchmark_version": metrics["benchmark_version"],
                "split": split,
                "ablation": name,
                "case_count": metrics["case_count"],
                "accuracy": metrics["accuracy"],
                "macro_f1": metrics["macro_f1"],
                "unsupported_classification_rate": metrics[
                    "unsupported_classification_rate"
                ],
                "explicit_limitation_rate": metrics["explicit_limitation_rate"],
                "proof_minimum_met_rate": metrics["proof_minimum_met_rate"],
                "policy_match_rate": metrics["policy_match_rate"],
                "unsafe_action_proposal_rate": metrics["unsafe_action_proposal_rate"],
                "replay_mismatch_count": metrics["replay_mismatch_count"],
                "delta_macro_f1_vs_full": round(metrics["macro_f1"] - base["macro_f1"], 6),
                "delta_unsupported_rate_vs_full": round(
                    metrics["unsupported_classification_rate"]
                    - base["unsupported_classification_rate"],
                    6,
                ),
                "notes": _ABLATION_NOTES.get(name, "Configured executable ablation."),
                "git_commit": metrics["git_commit"],
                "dataset_digest": metrics["dataset_digest"],
            }
        )
    return output


def _write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def compute_metrics(
    benchmark_input: Path,
    ablation_input: Path,
    *,
    out_dir: Path,
    benchmark_manifest: Path | None = None,
    ablation_manifest: Path | None = None,
) -> dict[str, Path]:
    """Generate all aggregate artifacts from raw executable-run outputs."""
    benchmark_rows = load_jsonl(benchmark_input)
    ablation_rows_raw = load_jsonl(ablation_input)
    _validate_raw_rows(
        benchmark_rows,
        expected_schema="research_prediction.v1",
        group_key="model_or_baseline",
    )
    _validate_raw_rows(
        ablation_rows_raw,
        expected_schema="research_ablation_prediction.v1",
        group_key="ablation",
    )
    benchmark_identity = (
        benchmark_rows[0]["benchmark_version"],
        benchmark_rows[0]["dataset_digest"],
        benchmark_rows[0]["git_commit"],
    )
    ablation_identity = (
        ablation_rows_raw[0]["benchmark_version"],
        ablation_rows_raw[0]["dataset_digest"],
        ablation_rows_raw[0]["git_commit"],
    )
    if benchmark_identity != ablation_identity:
        raise ValueError("benchmark and ablation raw rows come from different source identities")

    benchmark_manifest = benchmark_manifest or benchmark_input.with_name(
        "benchmark_run_manifest.json"
    )
    ablation_manifest = ablation_manifest or ablation_input.with_name(
        "ablation_run_manifest.json"
    )
    manifests = {
        "benchmark": json.loads(benchmark_manifest.read_text(encoding="utf-8")),
        "ablation": json.loads(ablation_manifest.read_text(encoding="utf-8")),
    }
    _validate_run_manifest(benchmark_rows, manifests["benchmark"], run_kind="benchmark")
    _validate_run_manifest(ablation_rows_raw, manifests["ablation"], run_kind="ablation")

    results, confusion = benchmark_metrics(benchmark_rows)
    ablations = ablation_metrics(ablation_rows_raw)

    paths = {
        "results": out_dir / "results.csv",
        "confusion_matrix": out_dir / "confusion_matrix.csv",
        "ablations": out_dir / "ablations.csv",
        "metrics": out_dir / "metrics.json",
        "environment": out_dir / "environment.json",
    }
    _write_csv(paths["results"], results, RESULT_FIELDS)
    _write_csv(paths["confusion_matrix"], confusion, CONFUSION_FIELDS)
    _write_csv(paths["ablations"], ablations, ABLATION_FIELDS)
    write_json(
        paths["metrics"],
        {
            "schema_version": "research_metrics.v1",
            "generated_at_utc": generated_at_utc(),
            "results": results,
            "confusion_matrix": confusion,
            "ablations": ablations,
        },
    )

    write_json(
        paths["environment"],
        {
            "schema_version": "research_environment.v1",
            "generated_at_utc": generated_at_utc(),
            "benchmark_run": manifests["benchmark"],
            "ablation_run": manifests["ablation"],
        },
    )
    return paths


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--benchmark-input",
        type=Path,
        default=ROOT / "experiments" / "results" / "benchmark_predictions.jsonl",
    )
    parser.add_argument(
        "--ablation-input",
        type=Path,
        default=ROOT / "experiments" / "results" / "ablation_predictions.jsonl",
    )
    parser.add_argument("--out-dir", type=Path, default=ROOT / "benchmarks")
    parser.add_argument("--benchmark-manifest", type=Path, default=None)
    parser.add_argument("--ablation-manifest", type=Path, default=None)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    paths = compute_metrics(
        args.benchmark_input,
        args.ablation_input,
        out_dir=args.out_dir,
        benchmark_manifest=args.benchmark_manifest,
        ablation_manifest=args.ablation_manifest,
    )
    for name, path in paths.items():
        print(f"wrote {name}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
