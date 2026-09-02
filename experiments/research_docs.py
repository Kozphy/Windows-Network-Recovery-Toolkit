"""Generate research documentation from machine-readable artifacts."""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

from experiments.dataset import repo_root
from experiments.report import generate_technical_report


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def generate_failure_analysis(*, results_dir: Path | None = None) -> Path:
    root = repo_root()
    errors = _read_csv(root / "benchmarks" / "error_analysis.csv")
    out = root / "docs" / "research" / "FAILURE_ANALYSIS.md"

    category_map = {
        "insufficient_evidence": "insufficient evidence",
        "contradictory_evidence": "ambiguous scenario",
        "label_ambiguity": "ambiguous scenario",
        "cross_signal_interaction": "wrong fault family",
        "proof_tier_failure": "unsupported but classified",
        "rule_boundary": "wrong fault family",
        "fixture_artifact": "dataset limitation",
        "unknown_requires_human_review": "ambiguous scenario",
    }

    counts: Counter[str] = Counter()
    examples: dict[str, list[str]] = {}
    for row in errors:
        raw = row.get("failure_category", "unknown")
        cat = category_map.get(raw, raw)
        counts[cat] += 1
        examples.setdefault(cat, [])
        if len(examples[cat]) < 3:
            examples[cat].append(row.get("case_id", ""))

    total = len(errors)
    lines = [
        "# Failure Analysis — Benchmark B3",
        "",
        "> Auto-generated from `benchmarks/error_analysis.csv`. Do not hand-edit counts.",
        "",
        f"**Total B3 misclassifications:** {total}",
        "",
        "## Summary by category",
        "",
        "| Category | Count | Rate | Example scenario IDs |",
        "|----------|------:|-----:|----------------------|",
    ]
    for cat, count in counts.most_common():
        rate = count / total if total else 0.0
        ex = ", ".join(examples.get(cat, [])[:3]) or "—"
        lines.append(f"| {cat} | {count} | {rate:.2%} | {ex} |")

    lines.extend(
        [
            "",
            "## Mitigation notes",
            "",
            "- **Insufficient evidence:** Add probes/listeners to sparse fixtures; do not lower abstention threshold without review.",
            "- **Wrong fault family:** Review label ambiguity vs classifier rule boundaries.",
            "- **Dataset limitation:** Expand v2 corpus; avoid rewriting labels to inflate metrics.",
            "",
            "## Reproduce",
            "",
            "```powershell",
            "python -m experiments.run_all",
            "```",
            "",
        ]
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def generate_claims_matrix(*, results_dir: Path | None = None) -> Path:
    root = repo_root()
    results = results_dir or (root / "experiments" / "results" / "latest")
    metrics = _read_csv(results / "metrics.csv")
    b3 = next((r for r in metrics if r.get("baseline") == "B3"), {})
    b1 = next((r for r in metrics if r.get("baseline") == "B1"), {})
    metadata_path = results / "metadata.json"
    git_sha = "unknown"
    if metadata_path.is_file():
        git_sha = json.loads(metadata_path.read_text(encoding="utf-8")).get("git_sha", "unknown")

    out = root / "docs" / "research" / "CLAIMS_EVIDENCE_MATRIX.md"
    lines = [
        "# Claims-to-Evidence Matrix",
        "",
        "| Claim | Type | Metric | Dataset | Baseline | Artifact | Supported? |",
        "|-------|------|--------|---------|----------|----------|------------|",
        "| Hash-chained audit implemented | Engineering | audit_verification_rate | N/A | B3 | safety_metrics.csv | Yes (code + test) |",
        f"| B3 macro F1 exceeds B1 on dataset v1 | Research | macro_f1 | v1 fixtures | B3 vs B1 | metrics.csv @ {git_sha[:8]} | "
        f"{'Yes' if float(b3.get('macro_f1', 0) or 0) > float(b1.get('macro_f1', 0) or 0) else 'Inconclusive'} "
        f"({b3.get('macro_f1', '?')} vs {b1.get('macro_f1', '?')}) |",
        "| Replay deterministic for B3 | Research | classification_agreement_rate | v1 | B3 | reproducibility_metrics.csv | Yes (1.0 on fixtures) |",
        "| Policy gate blocks unsafe proposals (A5) | Safety | unsafe_action_proposal_rate | v1 | B3 | ablations.csv | Supported in ablation |",
        "| Reduces enterprise MTTR | Product aspiration | — | — | — | — | **Not tested** |",
        "| Prevents all unsafe remediation | Safety (strong) | unsafe_action_proposal_rate=0 | v1 | B3 | safety_metrics.csv | Scoped to fixtures only |",
        "",
        "## Discipline",
        "",
        "- **Engineering claim:** verifiable from code/tests.",
        "- **Research claim:** requires benchmark artifact + dataset version + git SHA.",
        "- **Safety claim:** must scope to synthetic fixtures unless live trials exist.",
        "",
    ]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def generate_all_research_docs(*, results_dir: Path | None = None) -> dict[str, str]:
    """Generate full research documentation chain from artifacts."""
    tech = generate_technical_report(results_dir=results_dir)
    root = repo_root()
    docs_tech = root / "docs" / "research" / "TECHNICAL_REPORT.md"
    docs_tech.parent.mkdir(parents=True, exist_ok=True)
    docs_tech.write_text(tech.read_text(encoding="utf-8"), encoding="utf-8")
    failure = generate_failure_analysis(results_dir=results_dir)
    claims = generate_claims_matrix(results_dir=results_dir)
    return {
        "technical_report": str(docs_tech),
        "failure_analysis": str(failure),
        "claims_matrix": str(claims),
        "legacy_report": str(tech),
    }
