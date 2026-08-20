"""Build an evidence-linked Markdown report from generated benchmark artifacts."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _percent(value: str) -> str:
    return f"{float(value):.1%}"


def _cell(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def build_report(
    results_csv: Path,
    ablations_csv: Path,
    run_manifest: Path,
    *,
    out_path: Path,
) -> Path:
    """Render actual generated values without hard-coded benchmark claims."""
    results = _read_csv(results_csv)
    ablations = _read_csv(ablations_csv)
    manifest = json.loads(run_manifest.read_text(encoding="utf-8"))
    overall = sorted(
        (row for row in results if row["split"] == "all"),
        key=lambda row: row["model_or_baseline"],
    )
    held_out = sorted(
        (row for row in results if row["split"] == "held_out"),
        key=lambda row: row["model_or_baseline"],
    )
    ablation_overall = sorted(
        (row for row in ablations if row["split"] == "all"),
        key=lambda row: row["ablation"],
    )

    lines = [
        "# Synthetic research benchmark report",
        "",
        f"- Benchmark version: `{_cell(manifest['benchmark_version'])}`",
        f"- Dataset version: `{_cell(manifest['dataset']['version'])}`",
        f"- Synthetic case count: **{_cell(manifest['dataset']['case_count'])}**",
        f"- Dataset SHA-256: `{_cell(manifest['dataset']['sha256'])}`",
        f"- Source commit: `{_cell(manifest['git_commit'])}`",
        f"- Replay mismatch count: **{_cell(manifest['replay_mismatch_count'])}**",
        "",
        "> These are executed fixture results, not production telemetry, an external validation set, "
        "or evidence of population-level performance.",
        "",
        "## All synthetic splits",
        "",
        "| adapter | cases | accuracy | macro F1 | unsupported | policy match | replay mismatches |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in overall:
        lines.append(
            f"| {_cell(row['model_or_baseline'])} | {row['case_count']} | "
            f"{_percent(row['accuracy'])} | {_percent(row['macro_f1'])} | "
            f"{_percent(row['unsupported_classification_rate'])} | "
            f"{_percent(row['policy_match_rate'])} | {row['replay_mismatch_count']} |"
        )

    lines.extend(
        [
            "",
            "## Held-out synthetic split",
            "",
            "| adapter | cases | accuracy | macro F1 | proof minimum met | unsafe proposals |",
            "|---|---:|---:|---:|---:|---:|",
        ]
    )
    for row in held_out:
        lines.append(
            f"| {_cell(row['model_or_baseline'])} | {row['case_count']} | "
            f"{_percent(row['accuracy'])} | {_percent(row['macro_f1'])} | "
            f"{_percent(row['proof_minimum_met_rate'])} | "
            f"{_percent(row['unsafe_action_proposal_rate'])} |"
        )

    lines.extend(
        [
            "",
            "## Ablations across all synthetic splits",
            "",
            "| ablation | macro F1 | delta vs full | limitations present | unsafe proposals |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    for row in ablation_overall:
        lines.append(
            f"| {_cell(row['ablation'])} | {_percent(row['macro_f1'])} | "
            f"{float(row['delta_macro_f1_vs_full']):+.3f} | "
            f"{_percent(row['explicit_limitation_rate'])} | "
            f"{_percent(row['unsafe_action_proposal_rate'])} |"
        )

    lines.extend(
        [
            "",
            "## Interpretation boundaries",
            "",
            "- Results compare deterministic adapters on repository-authored synthetic fixtures only.",
            "- The `held_out` directory enforces workflow separation but is not an independent dataset.",
            "- Accuracy does not establish operational usefulness, MTTR improvement, or external validity.",
            "- The policy-gate ablation serializes counterfactual proposals; it never executes them.",
            "- Raw predictions and long-form confusion counts remain the authoritative evidence.",
            "",
            "## Reproduction",
            "",
            "```powershell",
            "python experiments/scripts/run_benchmark.py --config experiments/configs/benchmark-v1.json",
            "python experiments/scripts/run_ablations.py --config experiments/configs/ablations-v1.json",
            "python experiments/scripts/compute_metrics.py",
            "python experiments/scripts/build_report.py",
            "```",
            "",
        ]
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-csv", type=Path, default=ROOT / "benchmarks" / "results.csv")
    parser.add_argument(
        "--ablations-csv", type=Path, default=ROOT / "benchmarks" / "ablations.csv"
    )
    parser.add_argument(
        "--run-manifest",
        type=Path,
        default=ROOT / "experiments" / "results" / "benchmark_run_manifest.json",
    )
    parser.add_argument(
        "--out", type=Path, default=ROOT / "benchmarks" / "benchmark_report.md"
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    path = build_report(
        args.results_csv,
        args.ablations_csv,
        args.run_manifest,
        out_path=args.out,
    )
    print(f"wrote report: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
