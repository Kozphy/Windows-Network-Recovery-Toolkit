"""Generate technical report from machine-produced benchmark artifacts."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from experiments.dataset import repo_root


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def generate_technical_report(*, results_dir: Path | None = None) -> Path:
    root = repo_root()
    results = results_dir or (root / "experiments" / "results" / "latest")
    metadata_path = results / "metadata.json"
    metadata = (
        json.loads(metadata_path.read_text(encoding="utf-8")) if metadata_path.is_file() else {}
    )

    metrics = _read_csv(results / "metrics.csv")
    stats = _read_csv(root / "benchmarks" / "statistical_summary.csv")
    ablations = _read_csv(root / "benchmarks" / "ablations.csv")
    errors = _read_csv(root / "benchmarks" / "error_analysis.csv")
    repro = _read_csv(results / "reproducibility_metrics.csv")

    lines: list[str] = [
        "# Technical Report — Evidence-Tiered Endpoint Diagnosis Benchmark",
        "",
        "## Abstract",
        "",
        "Under controlled fixture benchmark dataset v1, we compare connectivity-only (B0),",
        "flat-rule (B1), single-signal WinINET (B2), and full platform (B3) baselines.",
        "All numerical claims below originate from generated artifacts in this repository.",
        "",
        "## Research Question",
        "",
        "Can deterministic, evidence-tiered endpoint diagnosis improve classification quality,",
        "auditability, safety, and decision reproducibility compared with simpler troubleshooting baselines?",
        "",
        "## Dataset",
        "",
        f"- Version: {metadata.get('dataset_version', 'v1')}",
        f"- Cases: {metadata.get('case_count', 'unknown')}",
        f"- Git SHA: `{metadata.get('git_sha', 'unknown')}`",
        f"- Run ID: `{metadata.get('run_id', 'unknown')}`",
        "",
        "## Baseline Results (classification)",
        "",
        "| Baseline | Accuracy | Macro F1 | Abstention rate | Exact matches |",
        "|----------|----------|----------|-----------------|---------------|",
    ]
    for row in metrics:
        lines.append(
            f"| {row['baseline']} | {row['accuracy']} | {row['macro_f1']} | "
            f"{row['abstention_rate']} | {row['exact_match_count']} |"
        )

    lines.extend(["", "## Statistical Analysis (bootstrap 95% CI)", ""])
    if stats:
        lines.append("| Metric | Baseline | Point | CI lower | CI upper | n |")
        lines.append("|--------|----------|-------|----------|----------|---|")
        for row in stats:
            if row["baseline"] == "B3":
                lines.append(
                    f"| {row['metric']} | {row['baseline']} | {row['point_estimate']} | "
                    f"{row['ci_lower']} | {row['ci_upper']} | {row['sample_size']} |"
                )
    else:
        lines.append("_No statistical summary artifact found._")

    lines.extend(["", "## Reproducibility", ""])
    for row in repro:
        lines.append(f"- **{row.get('metric', 'metric')}**: {row.get('value', '')}")

    lines.extend(["", "## Ablation Study (selected B3 deltas)", ""])
    if ablations:
        shown = 0
        for row in ablations:
            if row["metric"] != "macro_f1":
                continue
            lines.append(
                f"- **{row['ablation']}** ({row['ablation_name']}): "
                f"macro_f1 {row['full_system_value']} → {row['ablated_value']} "
                f"(Δ {row['absolute_delta']})"
            )
            shown += 1
            if shown >= 7:
                break
    else:
        lines.append("_No ablation artifact found._")

    lines.extend(["", "## Error Analysis (B3 failures)", ""])
    if errors:
        lines.append(f"Total B3 misclassifications: **{len(errors)}**")
        cats: dict[str, int] = {}
        for row in errors:
            cat = row["failure_category"]
            cats[cat] = cats.get(cat, 0) + 1
        for cat, count in sorted(cats.items(), key=lambda kv: -kv[1]):
            lines.append(f"- {cat}: {count}")
    else:
        lines.append("_No B3 failures or no error analysis artifact._")

    lines.extend(
        [
            "",
            "## Limitations",
            "",
            "- Fixture-synthetic evidence only; external validity to live enterprise endpoints is limited.",
            "- Macro metrics prioritized due to class imbalance.",
            "- Policy/safety metrics are synthetic governance checks, not proof of real-world safety.",
            "",
            "## Reproducibility",
            "",
            "```powershell",
            "$env:PYTHONPATH = (Get-Location).Path",
            "python -m experiments.run_all",
            "```",
            "",
            "Artifacts:",
            f"- `{results.relative_to(root).as_posix()}/metrics.csv`",
            "- `benchmarks/statistical_summary.csv`",
            "- `benchmarks/ablations.csv`",
            "- `benchmarks/error_analysis.csv`",
            "",
        ]
    )

    out_path = root / "research" / "technical_report.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out_path
