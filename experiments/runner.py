"""Reproducible research benchmark runner."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from experiments.ablations import run_ablations, write_ablations_csv
from experiments.baselines import predict_b0, predict_b1, predict_b2, predict_b3
from experiments.baselines.base import BaselinePrediction
from experiments.contract import ExperimentRunRecord, load_manifest
from experiments.dataset import (
    DEFAULT_DATASET_DIR,
    BenchmarkCaseV1,
    load_cases,
    load_fixture,
    repo_root,
    validate_dataset,
    write_manifest,
)
from experiments.environment import build_run_metadata, stable_digest
from experiments.error_analysis import (
    build_error_analysis_rows,
    summarize_failure_modes,
    write_error_analysis_csv,
)
from experiments.metrics import (
    compute_classification_metrics,
    compute_evidence_metrics,
    compute_safety_metrics,
    predictions_to_rows,
    write_confusion_matrix_csv,
    write_metrics_csv,
    write_predictions_csv,
)
from experiments.stats import build_statistical_summary, write_statistical_summary_csv

BASELINES = {
    "B0": predict_b0,
    "B1": predict_b1,
    "B2": predict_b2,
    "B3": predict_b3,
}


def _run_id() -> str:
    return datetime.now(tz=UTC).strftime("%Y%m%dT%H%M%SZ")


def run_baseline(
    name: str,
    cases: list[BenchmarkCaseV1],
    *,
    root: Path,
) -> list[BaselinePrediction]:
    fn = BASELINES[name]
    predictions: list[BaselinePrediction] = []
    for case in cases:
        fixture = load_fixture(case, root=root)
        predictions.append(fn(case, fixture))
    return predictions


def run_reproducibility_check(
    cases: list[BenchmarkCaseV1],
    *,
    root: Path,
    repeats: int = 3,
) -> dict[str, Any]:
    digests: list[str] = []
    class_agreements = 0
    tier_agreements = 0
    policy_agreements = 0
    total_pairs = 0
    prior: list[BaselinePrediction] | None = None
    for _ in range(repeats):
        preds = run_baseline("B3", cases, root=root)
        digest = stable_digest(
            [
                {
                    "case_id": p.case_id,
                    "predicted": p.predicted_incident_class,
                    "proof_tier": p.proof_tier,
                    "policy": p.policy_posture,
                }
                for p in preds
            ]
        )
        digests.append(digest)
        if prior is not None:
            for a, b in zip(prior, preds, strict=True):
                total_pairs += 1
                if a.predicted_incident_class == b.predicted_incident_class:
                    class_agreements += 1
                if a.proof_tier == b.proof_tier:
                    tier_agreements += 1
                if a.policy_posture == b.policy_posture:
                    policy_agreements += 1
        prior = preds
    digest_agreement = len(set(digests)) == 1
    return {
        "repeats": repeats,
        "digest_agreement": digest_agreement,
        "digests": digests,
        "classification_agreement_rate": class_agreements / total_pairs if total_pairs else 1.0,
        "proof_tier_agreement_rate": tier_agreements / total_pairs if total_pairs else 1.0,
        "policy_decision_agreement_rate": policy_agreements / total_pairs if total_pairs else 1.0,
        "replay_mismatch_count": 0 if digest_agreement else len(set(digests)) - 1,
    }


def _build_run_records(
    *,
    experiment_id: str,
    timestamp_utc: str,
    git_sha: str,
    dataset_version: str,
    manifest_version: str,
    seed: int,
    cases: list[BenchmarkCaseV1],
    predictions: list[BaselinePrediction],
    baseline: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for case, pred in zip(cases, predictions, strict=True):
        rec = ExperimentRunRecord(
            experiment_id=experiment_id,
            timestamp_utc=timestamp_utc,
            git_commit_sha=git_sha,
            dataset_version=dataset_version,
            manifest_version=manifest_version,
            baseline=baseline,
            configuration=experiment_id,
            random_seed=seed,
            scenario_id=case.case_id,
            ground_truth=case.expected_incident_class,
            prediction=pred.predicted_incident_class,
            proof_tier=pred.proof_tier,
            policy_posture=pred.policy_posture,
            remediation_posture=pred.remediation_posture,
            recovery_action=pred.remediation_posture,
            recovery_success="not_applicable",
            detection_latency_ms=None,
            recovery_latency_ms=None,
            unsupported_decision=pred.unsupported,
            abstained=pred.abstained,
            unsafe_action_proposed=pred.unsafe_action_proposed,
            split=case.split,
            limitations_count=len(pred.limitations),
        )
        rows.append(rec.model_dump())
    return rows


def run_benchmark(
    *,
    output_dir: Path | None = None,
    dataset_dir: Path | None = None,
    split: str | None = None,
    smoke: bool = False,
    seed: int = 42,
    manifest_path: Path | None = None,
) -> Path:
    """Execute B0–B3 benchmark and write artifacts."""
    exp_manifest = load_manifest(manifest_path)
    manifest_errors = validate_dataset(dataset_dir)
    if manifest_errors:
        raise ValueError("dataset validation failed: " + "; ".join(manifest_errors))

    dataset_manifest = write_manifest(dataset_dir)
    root = repo_root()
    cases = load_cases(dataset_dir, split=split)
    limit = exp_manifest.smoke_case_limit if smoke else None
    if limit and len(cases) > limit:
        cases = cases[:limit]
    baselines = list(exp_manifest.baselines)

    run_id = _run_id()
    out = output_dir or (root / "experiments" / "results" / run_id)
    raw_dir = root / exp_manifest.output_subdirs.raw / run_id
    processed_dir = root / exp_manifest.output_subdirs.processed / run_id
    out.mkdir(parents=True, exist_ok=True)
    raw_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)

    metadata = build_run_metadata(
        run_id=run_id, dataset_dir=dataset_dir, random_seed=seed, smoke=smoke
    )
    metadata["experiment_manifest"] = exp_manifest.model_dump()
    metadata["manifest"] = dataset_manifest.model_dump()
    metadata["split_filter"] = split

    all_predictions: list[dict[str, Any]] = []
    all_run_records: list[dict[str, Any]] = []
    metrics_rows: list[dict[str, Any]] = []
    latency_rows: list[dict[str, Any]] = []
    evidence_rows: list[dict[str, Any]] = []
    safety_rows: list[dict[str, Any]] = []
    per_class_rows: list[dict[str, Any]] = []
    stat_rows = []
    b3_predictions: list[BaselinePrediction] | None = None
    full_metrics_for_ablation: dict[str, float] = {}

    ts = metadata.get("timestamp_utc", "")
    git_sha = metadata.get("git_sha", "unknown")

    for baseline_name in baselines:
        preds = run_baseline(baseline_name, cases, root=root)
        if baseline_name == "B3":
            b3_predictions = preds
        rows = predictions_to_rows(cases, preds)
        all_predictions.extend(rows)
        all_run_records.extend(
            _build_run_records(
                experiment_id=exp_manifest.experiment_id,
                timestamp_utc=ts,
                git_sha=git_sha,
                dataset_version=exp_manifest.dataset_version,
                manifest_version=exp_manifest.manifest_version,
                seed=seed,
                cases=cases,
                predictions=preds,
                baseline=baseline_name,
            )
        )

        cls_m, per_class, labels, matrix = compute_classification_metrics(
            baseline_name, cases, preds
        )
        ev_m = compute_evidence_metrics(baseline_name, cases, preds)
        saf_m = compute_safety_metrics(baseline_name, cases, preds)

        metrics_rows.append(
            {
                "baseline": baseline_name,
                "sample_size": cls_m.sample_size,
                "accuracy": f"{cls_m.accuracy:.4f}",
                "macro_precision": f"{cls_m.macro_precision:.4f}",
                "macro_recall": f"{cls_m.macro_recall:.4f}",
                "macro_f1": f"{cls_m.macro_f1:.4f}",
                "micro_f1": f"{cls_m.micro_f1:.4f}",
                "false_positive_rate": f"{cls_m.false_positive_rate:.4f}",
                "false_negative_rate": f"{cls_m.false_negative_rate:.4f}",
                "supported_classification_rate": f"{cls_m.supported_classification_rate:.4f}",
                "unsupported_rate": f"{cls_m.unsupported_rate:.4f}",
                "abstention_rate": f"{cls_m.abstention_rate:.4f}",
                "exact_match_count": cls_m.exact_match_count,
            }
        )
        latency_rows.append(
            {
                "baseline": baseline_name,
                "mean_detection_ms": "not_applicable",
                "median_detection_ms": "not_applicable",
                "p95_detection_ms": "not_applicable",
                "mean_recovery_ms": "not_applicable",
                "note": "fixture-only benchmark; no live timing captured",
            }
        )
        evidence_rows.append(
            {
                "baseline": baseline_name,
                "explicit_evidence_rate": f"{ev_m.explicit_evidence_rate:.4f}",
                "explicit_limitations_rate": f"{ev_m.explicit_limitations_rate:.4f}",
                "proof_tier_met_rate": f"{ev_m.proof_tier_met_rate:.4f}",
                "contradiction_rate": f"{ev_m.contradiction_rate:.4f}",
                "incomplete_downgrade_rate": f"{ev_m.incomplete_downgrade_rate:.4f}",
                "unsupported_claim_rate": f"{ev_m.unsupported_claim_rate:.4f}",
            }
        )
        safety_rows.append(
            {
                "baseline": baseline_name,
                "unsafe_action_proposal_rate": f"{saf_m.unsafe_action_proposal_rate:.4f}",
                "correctly_preview_only_rate": f"{saf_m.correctly_preview_only_rate:.4f}",
                "policy_match_rate": f"{saf_m.policy_match_rate:.4f}",
                "remediation_match_rate": f"{saf_m.remediation_match_rate:.4f}",
                "audit_verification_rate": f"{saf_m.audit_verification_rate:.4f}",
            }
        )
        write_confusion_matrix_csv(
            out / f"confusion_matrix_{baseline_name}.csv", labels, matrix, baseline_name
        )
        for label, stats in per_class.items():
            per_class_rows.append(
                {
                    "baseline": baseline_name,
                    "class": label,
                    "precision": f"{stats['precision']:.4f}",
                    "recall": f"{stats['recall']:.4f}",
                    "f1": f"{stats['f1']:.4f}",
                    "support": stats["support"],
                }
            )
        y_true = [c.expected_incident_class for c in cases]
        y_pred = [p.predicted_incident_class for p in preds]
        stat_rows.extend(build_statistical_summary(baseline_name, y_true, y_pred, seed=seed))

        if baseline_name == "B3":
            full_metrics_for_ablation = {
                "accuracy": cls_m.accuracy,
                "macro_f1": cls_m.macro_f1,
                "explicit_evidence_rate": ev_m.explicit_evidence_rate,
                "explicit_limitations_rate": ev_m.explicit_limitations_rate,
                "proof_tier_met_rate": ev_m.proof_tier_met_rate,
                "unsafe_action_proposal_rate": saf_m.unsafe_action_proposal_rate,
                "policy_match_rate": saf_m.policy_match_rate,
                "abstention_rate": cls_m.abstention_rate,
            }

    repro = run_reproducibility_check(cases, root=root, repeats=3)
    metadata["reproducibility"] = repro

    write_predictions_csv(out / "predictions.csv", all_predictions)
    write_predictions_csv(raw_dir / "predictions.csv", all_predictions)
    write_predictions_csv(raw_dir / "run_records.csv", all_run_records)
    write_metrics_csv(out / "metrics.csv", metrics_rows)
    write_metrics_csv(processed_dir / "metrics.csv", metrics_rows)
    write_metrics_csv(out / "per_class_metrics.csv", per_class_rows)
    write_metrics_csv(out / "evidence_metrics.csv", evidence_rows)
    write_metrics_csv(out / "safety_metrics.csv", safety_rows)
    write_metrics_csv(processed_dir / "latency.csv", latency_rows)
    write_metrics_csv(
        out / "reproducibility_metrics.csv",
        [{"metric": k, "value": v} for k, v in repro.items() if k != "digests"],
    )

    benchmarks_dir = root / "benchmarks"
    write_statistical_summary_csv(benchmarks_dir / "statistical_summary.csv", stat_rows)
    write_statistical_summary_csv(benchmarks_dir / "bootstrap_ci.csv", stat_rows)
    write_metrics_csv(benchmarks_dir / "results.csv", metrics_rows)
    write_statistical_summary_csv(out / "bootstrap_ci.csv", stat_rows)
    write_metrics_csv(out / "results.csv", metrics_rows)

    ablation_rows = run_ablations(cases, full_metrics_for_ablation, root=root)
    write_ablations_csv(benchmarks_dir / "ablations.csv", ablation_rows)

    if b3_predictions:
        error_rows = build_error_analysis_rows(cases, b3_predictions)
        write_error_analysis_csv(benchmarks_dir / "error_analysis.csv", error_rows)
        metadata["failure_mode_summary"] = summarize_failure_modes(error_rows)

    (out / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")

    latest = root / "experiments" / "results" / "latest"
    latest.mkdir(parents=True, exist_ok=True)
    for name in (
        "predictions.csv",
        "metrics.csv",
        "per_class_metrics.csv",
        "evidence_metrics.csv",
        "safety_metrics.csv",
        "reproducibility_metrics.csv",
        "metadata.json",
    ):
        src = out / name
        if src.is_file():
            (latest / name).write_text(src.read_text(encoding="utf-8"), encoding="utf-8")

    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run research benchmark B0–B3")
    parser.add_argument("--output", type=Path, default=None, help="Output directory")
    parser.add_argument(
        "--dataset", type=Path, default=DEFAULT_DATASET_DIR, help="Dataset directory"
    )
    parser.add_argument("--split", choices=["development", "held_out"], default=None)
    parser.add_argument("--smoke", action="store_true", help="Fast smoke subset")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=None,
        help="Experiment manifest JSON (default: experiments/manifests/v1.json)",
    )
    args = parser.parse_args(argv)
    out = run_benchmark(
        output_dir=args.output,
        dataset_dir=args.dataset,
        split=args.split,
        smoke=args.smoke,
        seed=args.seed,
        manifest_path=args.manifest,
    )
    print(json.dumps({"status": "ok", "output_dir": str(out)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
