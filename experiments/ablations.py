"""Ablation study A1–A7."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from experiments.baselines.b3_full_platform import AblationConfig, predict_b3
from experiments.dataset import BenchmarkCaseV1, load_fixture, repo_root
from experiments.metrics import (
    compute_classification_metrics,
    compute_evidence_metrics,
    compute_safety_metrics,
)


@dataclass(frozen=True)
class AblationSpec:
    code: str
    name: str
    config: AblationConfig
    notes: str


ABLATIONS: list[AblationSpec] = [
    AblationSpec(
        "A1", "remove_proof_tiers", AblationConfig(remove_proof_tiers=True), "Force T0 tier"
    ),
    AblationSpec(
        "A2",
        "remove_listener_process",
        AblationConfig(remove_listener_process=True),
        "Strip listener/process evidence",
    ),
    AblationSpec(
        "A3",
        "remove_tls_path",
        AblationConfig(remove_tls_path=True),
        "Strip TLS/path/browser probe evidence",
    ),
    AblationSpec(
        "A4", "remove_limitations", AblationConfig(remove_limitations=True), "Clear limitations[]"
    ),
    AblationSpec(
        "A5", "remove_policy_gate", AblationConfig(remove_policy_gate=True), "Policy always ALLOW"
    ),
    AblationSpec(
        "A6", "remove_hash_chain", AblationConfig(remove_hash_chain=True), "Audit chain ablated"
    ),
    AblationSpec(
        "A7",
        "remove_cross_signal_aggregation",
        AblationConfig(remove_cross_signal_aggregation=True),
        "Flat rules instead of aggregation",
    ),
]


def _metric_value(name: str, cls: Any, ev: Any, saf: Any) -> float:
    mapping = {
        "accuracy": cls.accuracy,
        "macro_f1": cls.macro_f1,
        "explicit_evidence_rate": ev.explicit_evidence_rate,
        "explicit_limitations_rate": ev.explicit_limitations_rate,
        "proof_tier_met_rate": ev.proof_tier_met_rate,
        "unsafe_action_proposal_rate": saf.unsafe_action_proposal_rate,
        "policy_match_rate": saf.policy_match_rate,
        "abstention_rate": cls.abstention_rate,
    }
    return float(mapping[name])


def run_ablations(
    cases: list[BenchmarkCaseV1],
    full_metrics: dict[str, float],
    *,
    root: Path | None = None,
) -> list[dict[str, Any]]:
    base = root or repo_root()
    rows: list[dict[str, Any]] = []
    metric_names = list(full_metrics.keys())

    full_predictions = []
    for case in cases:
        fixture = load_fixture(case, root=base)
        full_predictions.append(predict_b3(case, fixture))

    for spec in ABLATIONS:
        predictions = []
        for case in cases:
            fixture = load_fixture(case, root=base)
            predictions.append(
                predict_b3(case, fixture, ablation=spec.config, baseline_label=f"B3_{spec.code}")
            )
        cls_m, _, labels, matrix = compute_classification_metrics(spec.code, cases, predictions)
        ev_m = compute_evidence_metrics(spec.code, cases, predictions)
        saf_m = compute_safety_metrics(spec.code, cases, predictions)
        ablated = {
            "accuracy": cls_m.accuracy,
            "macro_f1": cls_m.macro_f1,
            "explicit_evidence_rate": ev_m.explicit_evidence_rate,
            "explicit_limitations_rate": ev_m.explicit_limitations_rate,
            "proof_tier_met_rate": ev_m.proof_tier_met_rate,
            "unsafe_action_proposal_rate": saf_m.unsafe_action_proposal_rate,
            "policy_match_rate": saf_m.policy_match_rate,
            "abstention_rate": cls_m.abstention_rate,
        }
        for metric in metric_names:
            full_val = full_metrics[metric]
            ab_val = ablated[metric]
            delta = ab_val - full_val
            rel = (delta / full_val) if full_val else 0.0
            rows.append(
                {
                    "ablation": spec.code,
                    "ablation_name": spec.name,
                    "metric": metric,
                    "full_system_value": f"{full_val:.4f}",
                    "ablated_value": f"{ab_val:.4f}",
                    "absolute_delta": f"{delta:.4f}",
                    "relative_delta": f"{rel:.4f}",
                    "sample_size": len(cases),
                    "notes": spec.notes,
                }
            )
    return rows


def write_ablations_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "ablation",
        "ablation_name",
        "metric",
        "full_system_value",
        "ablated_value",
        "absolute_delta",
        "relative_delta",
        "sample_size",
        "notes",
    ]
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
