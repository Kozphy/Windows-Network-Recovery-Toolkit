"""Write machine-readable artifacts and research documentation."""

from __future__ import annotations

import csv
import json
import subprocess
from pathlib import Path

from research.interactions.analysis import analyze_experiment
from research.interactions.experiment import (
    EXPERIMENT_BUILDERS,
    cases_digest,
    run_interaction_experiments,
    run_timestamp,
)
from research.interactions.models import InteractionAnalysisResult, InteractionRunManifest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_OUT = _REPO_ROOT / "experiments" / "results"


def _git_sha() -> str:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=_REPO_ROOT,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        return out.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def write_interaction_cases_jsonl(path: Path, observations: list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in observations:
            fh.write(json.dumps(row.model_dump(mode="json"), sort_keys=True) + "\n")


def write_interaction_effects_csv(path: Path, analyses: list[InteractionAnalysisResult]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "experiment_id",
        "factor_a",
        "factor_b",
        "outcome",
        "main_effect_x1",
        "main_effect_x2",
        "interaction_effect",
        "lpm_beta_0",
        "lpm_beta_1",
        "lpm_beta_2",
        "lpm_beta_3",
        "sample_size",
        "ci_lower",
        "ci_upper",
        "ci_method",
        "effect_size_label",
        "limitations",
    ]
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for analysis in analyses:
            for effect in analysis.effects:
                writer.writerow(
                    {
                        "experiment_id": analysis.experiment_id,
                        "factor_a": analysis.factor_a_name,
                        "factor_b": analysis.factor_b_name,
                        "outcome": effect.outcome,
                        "main_effect_x1": f"{effect.main_effect_x1:.4f}",
                        "main_effect_x2": f"{effect.main_effect_x2:.4f}",
                        "interaction_effect": f"{effect.interaction_effect:.4f}",
                        "lpm_beta_0": f"{effect.lpm_beta_0:.4f}",
                        "lpm_beta_1": f"{effect.lpm_beta_1:.4f}",
                        "lpm_beta_2": f"{effect.lpm_beta_2:.4f}",
                        "lpm_beta_3": f"{effect.lpm_beta_3:.4f}",
                        "sample_size": effect.sample_size,
                        "ci_lower": "" if effect.ci_lower is None else f"{effect.ci_lower:.4f}",
                        "ci_upper": "" if effect.ci_upper is None else f"{effect.ci_upper:.4f}",
                        "ci_method": effect.ci_method or "",
                        "effect_size_label": effect.effect_size_label,
                        "limitations": " | ".join(effect.limitations[:2]),
                    }
                )


def write_interaction_summary_json(
    path: Path,
    *,
    analyses: list[InteractionAnalysisResult],
    manifest: InteractionRunManifest,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "manifest": manifest.model_dump(),
        "experiments": [a.model_dump(mode="json") for a in analyses],
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def generate_markdown_report(
    path: Path,
    analyses: list[InteractionAnalysisResult],
    manifest: InteractionRunManifest,
) -> None:
    lines = [
        "# Interaction Effects — Research Report",
        "",
        "> Machine-generated from `experiments/results/interaction_*.` artifacts. "
        "Do not hand-edit metric values.",
        "",
        "## Purpose",
        "",
        "Phase 1 tests whether combined fault factors produce outcomes beyond",
        "the sum of individual main effects on controlled factorial fixtures.",
        "",
        f"- **Run timestamp:** {manifest.timestamp_utc}",
        f"- **Git SHA:** `{manifest.git_sha}`",
        f"- **Cases:** {manifest.case_count}",
        f"- **Experiments:** {manifest.experiment_count}",
        "",
        "## Model",
        "",
        "```text",
        "Y = β0 + β1·X1 + β2·X2 + β3·(X1 × X2)",
        "```",
        "",
        "Interaction contrast reported as: **Y11 − Y10 − Y01 + Y00** (cell means).",
        "",
        "## Results",
        "",
    ]
    for analysis in analyses:
        lines.append(f"### {analysis.experiment_id}")
        lines.append("")
        lines.append(f"**Factors:** {analysis.factor_a_name} × {analysis.factor_b_name}")
        lines.append("")
        lines.append(f"{analysis.description}")
        lines.append("")
        lines.append("| Outcome | Main X1 | Main X2 | Interaction | n | 95% CI |")
        lines.append("|---------|---------|---------|-------------|---|--------|")
        for effect in analysis.effects:
            ci = (
                f"{effect.ci_lower:.3f}–{effect.ci_upper:.3f}"
                if effect.ci_lower is not None and effect.ci_upper is not None
                else "n/a"
            )
            lines.append(
                f"| {effect.outcome} | {effect.main_effect_x1:.4f} | "
                f"{effect.main_effect_x2:.4f} | {effect.interaction_effect:.4f} | "
                f"{effect.sample_size} | {ci} |"
            )
        lines.append("")

    lines.extend(
        [
            "## Limitations",
            "",
            "- Synthetic factorial fixtures only.",
            "- Small sample per experiment (12 cases with 3 replicates/cell).",
            "- Bootstrap CIs are exploratory — not confirmatory significance tests.",
            "- Platform outcomes may diverge from designed ground-truth severity.",
            "",
            "## Reproduce",
            "",
            "```powershell",
            "$env:PYTHONPATH = (Get-Location).Path",
            "python -m research.interactions",
            "# or: make research-interactions",
            "```",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_and_report(
    *,
    output_dir: Path | None = None,
    replicates: int = 3,
    seed: int = 42,
) -> Path:
    """Execute interaction experiments and write all artifacts."""
    out = output_dir or _DEFAULT_OUT
    observations, cases = run_interaction_experiments(replicates=replicates)
    digest = cases_digest(cases)
    git_sha = _git_sha()
    ts = run_timestamp()

    analyses: list[InteractionAnalysisResult] = []
    for spec in EXPERIMENT_BUILDERS:
        analyses.append(
            analyze_experiment(
                spec["experiment_id"],
                observations,
                factor_a_name=spec["factor_a_name"],
                factor_b_name=spec["factor_b_name"],
                description=spec["description"],
                git_sha=git_sha,
                dataset_digest=digest,
                seed=seed,
            )
        )

    manifest = InteractionRunManifest(
        experiment_count=len(analyses),
        case_count=len(observations),
        git_sha=git_sha,
        random_seed=seed,
        timestamp_utc=ts,
        experiments=[a.experiment_id for a in analyses],
    )

    write_interaction_cases_jsonl(out / "interaction_cases.jsonl", observations)
    write_interaction_effects_csv(out / "interaction_effects.csv", analyses)
    write_interaction_summary_json(
        out / "interaction_summary.json", analyses=analyses, manifest=manifest
    )

    docs_path = _REPO_ROOT / "docs" / "research" / "interaction_effects.md"
    generate_markdown_report(docs_path, analyses, manifest)

    return out


def main() -> int:
    out = run_and_report()
    print(json.dumps({"status": "ok", "output_dir": str(out)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
