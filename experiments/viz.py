"""Research benchmark visualization and Power BI export.

Generates:
- Self-contained HTML dashboard (Chart.js, offline-capable if cached)
- Power BI-ready CSV tables under ``analytics/powerbi/research/data/``
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from dataclasses import dataclass, field
from html import escape
from pathlib import Path
from typing import Any

from experiments.dataset import repo_root

DEFAULT_RESULTS_DIR = repo_root() / "experiments" / "results" / "latest"
DEFAULT_BENCHMARKS_DIR = repo_root() / "benchmarks"
DEFAULT_HTML_OUT = repo_root() / "benchmarks" / "reports" / "research_dashboard.html"
DEFAULT_POWERBI_OUT = repo_root() / "analytics" / "powerbi" / "research" / "data"


@dataclass
class ResearchArtifacts:
    """Loaded benchmark artifacts for visualization."""

    metadata: dict[str, Any] = field(default_factory=dict)
    metrics: list[dict[str, str]] = field(default_factory=list)
    bootstrap_ci: list[dict[str, str]] = field(default_factory=list)
    ablations: list[dict[str, str]] = field(default_factory=list)
    error_analysis: list[dict[str, str]] = field(default_factory=list)
    per_class: list[dict[str, str]] = field(default_factory=list)
    confusion_b3: list[dict[str, str]] = field(default_factory=list)
    results_dir: Path = field(default_factory=lambda: DEFAULT_RESULTS_DIR)


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def load_artifacts(
    *,
    results_dir: Path | None = None,
    benchmarks_dir: Path | None = None,
) -> ResearchArtifacts:
    """Load research CSV/JSON artifacts from latest run and benchmarks dir."""
    root = repo_root()
    results = results_dir or (root / "experiments" / "results" / "latest")
    benchmarks = benchmarks_dir or (root / "benchmarks")

    metadata: dict[str, Any] = {}
    meta_path = results / "metadata.json"
    if meta_path.is_file():
        metadata = json.loads(meta_path.read_text(encoding="utf-8"))

    confusion_b3 = _read_csv(results / "confusion_matrix_B3.csv")
    if not confusion_b3:
        for candidate in sorted(
            (root / "experiments" / "results").glob("*/confusion_matrix_B3.csv")
        ):
            confusion_b3 = _read_csv(candidate)
            if confusion_b3:
                break

    return ResearchArtifacts(
        metadata=metadata,
        metrics=_read_csv(benchmarks / "results.csv"),
        bootstrap_ci=_read_csv(benchmarks / "bootstrap_ci.csv"),
        ablations=_read_csv(benchmarks / "ablations.csv"),
        error_analysis=_read_csv(benchmarks / "error_analysis.csv"),
        per_class=_read_csv(results / "per_class_metrics.csv"),
        confusion_b3=confusion_b3,
        results_dir=results,
    )


def validate_artifacts(artifacts: ResearchArtifacts) -> list[str]:
    """Return human-readable errors when required artifacts are missing."""
    errors: list[str] = []
    if not artifacts.metrics:
        errors.append("missing benchmarks/results.csv — run: python -m experiments.run_benchmark")
    if not artifacts.bootstrap_ci:
        errors.append("missing benchmarks/bootstrap_ci.csv")
    return errors


def export_powerbi_tables(
    artifacts: ResearchArtifacts,
    out_dir: Path | None = None,
) -> Path:
    """Export flattened CSV tables for Power BI Desktop import."""
    target = out_dir or DEFAULT_POWERBI_OUT
    target.mkdir(parents=True, exist_ok=True)

    meta = artifacts.metadata
    run_id = str(meta.get("run_id", "unknown"))
    git_sha = str(meta.get("git_sha", "unknown"))[:12]
    dataset_version = str(meta.get("dataset_version", "v1"))
    case_count = str(meta.get("case_count", ""))

    dim_baseline: list[dict[str, str]] = []
    for row in artifacts.metrics:
        baseline = row.get("baseline", "")
        dim_baseline.append(
            {
                "baseline_key": baseline,
                "baseline_name": _baseline_label(baseline),
                "description": _baseline_description(baseline),
                "run_id": run_id,
                "git_sha": git_sha,
                "dataset_version": dataset_version,
            }
        )
    _write_csv(target / "dim_baseline.csv", dim_baseline)

    fact_metrics: list[dict[str, str]] = []
    for row in artifacts.metrics:
        baseline = row.get("baseline", "")
        for metric_key in (
            "accuracy",
            "macro_f1",
            "micro_f1",
            "macro_precision",
            "macro_recall",
            "false_positive_rate",
            "false_negative_rate",
            "supported_classification_rate",
            "unsupported_rate",
            "abstention_rate",
        ):
            val = row.get(metric_key, "")
            if val:
                fact_metrics.append(
                    {
                        "baseline_key": baseline,
                        "metric_name": metric_key,
                        "metric_value": val,
                        "sample_size": row.get("sample_size", case_count),
                        "run_id": run_id,
                        "git_sha": git_sha,
                        "dataset_version": dataset_version,
                    }
                )
    _write_csv(target / "fact_benchmark_metrics.csv", fact_metrics)

    fact_ci: list[dict[str, str]] = []
    for row in artifacts.bootstrap_ci:
        fact_ci.append(
            {
                "baseline_key": row.get("baseline", ""),
                "metric_name": row.get("metric", ""),
                "point_estimate": row.get("point_estimate", ""),
                "ci_lower": row.get("ci_lower", ""),
                "ci_upper": row.get("ci_upper", ""),
                "sample_size": row.get("sample_size", ""),
                "n_bootstrap": row.get("n_bootstrap", ""),
                "random_seed": row.get("random_seed", ""),
                "run_id": run_id,
                "git_sha": git_sha,
            }
        )
    _write_csv(target / "fact_bootstrap_ci.csv", fact_ci)

    fact_ablations: list[dict[str, str]] = []
    for row in artifacts.ablations:
        fact_ablations.append(
            {
                "ablation_key": row.get("ablation", ""),
                "ablation_name": row.get("ablation_name", ""),
                "metric_name": row.get("metric", ""),
                "full_system_value": row.get("full_system_value", ""),
                "ablated_value": row.get("ablated_value", ""),
                "absolute_delta": row.get("absolute_delta", ""),
                "relative_delta": row.get("relative_delta", ""),
                "sample_size": row.get("sample_size", case_count),
                "notes": row.get("notes", ""),
                "run_id": run_id,
                "git_sha": git_sha,
            }
        )
    _write_csv(target / "fact_ablations.csv", fact_ablations)

    fact_failures: list[dict[str, str]] = []
    for row in artifacts.error_analysis:
        fact_failures.append(
            {
                "case_id": row.get("case_id", ""),
                "expected_class": row.get("expected", ""),
                "predicted_class": row.get("predicted", ""),
                "failure_category": row.get("failure_category", ""),
                "proof_tier": row.get("proof_tier", ""),
                "ambiguity_allowed": row.get("ambiguity_allowed", ""),
                "run_id": run_id,
                "git_sha": git_sha,
            }
        )
    _write_csv(target / "fact_b3_failures.csv", fact_failures)

    fact_confusion: list[dict[str, str]] = []
    for row in artifacts.confusion_b3:
        expected = row.get("expected\\predicted") or row.get("expected/predicted", "")
        for key, val in row.items():
            if key in {"baseline", "expected\\predicted", "expected/predicted"}:
                continue
            fact_confusion.append(
                {
                    "baseline_key": row.get("baseline", "B3"),
                    "expected_class": expected,
                    "predicted_class": key,
                    "count": val,
                    "run_id": run_id,
                    "git_sha": git_sha,
                }
            )
    _write_csv(target / "fact_confusion_matrix_b3.csv", fact_confusion)

    manifest = {
        "schema_version": "research_powerbi_export.v1",
        "run_id": run_id,
        "git_sha": git_sha,
        "dataset_version": dataset_version,
        "case_count": case_count,
        "tables": [
            "dim_baseline.csv",
            "fact_benchmark_metrics.csv",
            "fact_bootstrap_ci.csv",
            "fact_ablations.csv",
            "fact_b3_failures.csv",
            "fact_confusion_matrix_b3.csv",
        ],
    }
    (target / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return target


def generate_html_dashboard(
    artifacts: ResearchArtifacts,
    out_path: Path | None = None,
) -> Path:
    """Render a self-contained HTML research dashboard."""
    errors = validate_artifacts(artifacts)
    if errors:
        raise FileNotFoundError("; ".join(errors))

    target = out_path or DEFAULT_HTML_OUT
    target.parent.mkdir(parents=True, exist_ok=True)

    meta = artifacts.metadata
    git_sha = str(meta.get("git_sha", "unknown"))[:12]
    run_id = str(meta.get("run_id", "unknown"))
    case_count = meta.get("case_count", "?")
    seed = meta.get("random_seed", "?")

    baselines = [r["baseline"] for r in artifacts.metrics]
    macro_f1 = [float(r["macro_f1"]) for r in artifacts.metrics]
    accuracy = [float(r["accuracy"]) for r in artifacts.metrics]
    abstention = [float(r["abstention_rate"]) for r in artifacts.metrics]

    ci_by_baseline: dict[str, dict[str, tuple[float, float, float]]] = {}
    for row in artifacts.bootstrap_ci:
        bl = row.get("baseline", "")
        metric = row.get("metric", "")
        ci_by_baseline.setdefault(bl, {})[metric] = (
            float(row.get("point_estimate", 0)),
            float(row.get("ci_lower", 0)),
            float(row.get("ci_upper", 0)),
        )

    f1_ci_lower = [
        ci_by_baseline.get(b, {}).get("macro_f1", (macro_f1[i], 0, 0))[1]
        for i, b in enumerate(baselines)
    ]
    f1_ci_upper = [
        ci_by_baseline.get(b, {}).get("macro_f1", (macro_f1[i], 0, 0))[2]
        for i, b in enumerate(baselines)
    ]

    ablation_macro = _ablation_macro_f1_deltas(artifacts.ablations)
    failure_counts = Counter(r.get("failure_category", "unknown") for r in artifacts.error_analysis)

    chart_payload = json.dumps(
        {
            "baselines": baselines,
            "baselineLabels": [_baseline_label(b) for b in baselines],
            "macroF1": macro_f1,
            "accuracy": accuracy,
            "abstention": abstention,
            "f1CiLower": f1_ci_lower,
            "f1CiUpper": f1_ci_upper,
            "ablationLabels": [a["label"] for a in ablation_macro],
            "ablationDeltas": [a["delta"] for a in ablation_macro],
            "failureLabels": list(failure_counts.keys()),
            "failureCounts": list(failure_counts.values()),
        }
    )

    confusion_html = _render_confusion_table(artifacts.confusion_b3)
    failures_html = _render_failures_table(artifacts.error_analysis[:12])

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Research Benchmark Dashboard — Dataset v1</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
  <style>
    :root {{
      --bg: #0f1419; --card: #1a2332; --text: #e7ecf3; --muted: #8b9cb3;
      --accent: #3b82f6; --warn: #f59e0b; --ok: #10b981; --border: #2d3a4f;
    }}
    * {{ box-sizing: border-box; }}
    body {{ font-family: "Segoe UI", system-ui, sans-serif; background: var(--bg); color: var(--text); margin: 0; padding: 1.5rem; }}
    h1 {{ font-size: 1.5rem; margin: 0 0 0.25rem; }}
    .subtitle {{ color: var(--muted); font-size: 0.9rem; margin-bottom: 1.5rem; }}
    .banner {{ background: #422006; border: 1px solid #92400e; color: #fde68a; padding: 0.75rem 1rem; border-radius: 8px; margin-bottom: 1.5rem; font-size: 0.85rem; }}
    .grid {{ display: grid; gap: 1rem; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); }}
    .card {{ background: var(--card); border: 1px solid var(--border); border-radius: 10px; padding: 1rem; }}
    .card h2 {{ font-size: 1rem; margin: 0 0 0.75rem; color: var(--muted); font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em; }}
    .meta {{ display: flex; flex-wrap: wrap; gap: 1rem; margin-bottom: 1.5rem; }}
    .meta span {{ background: var(--card); border: 1px solid var(--border); padding: 0.4rem 0.75rem; border-radius: 6px; font-size: 0.8rem; }}
    canvas {{ max-height: 280px; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 0.78rem; }}
    th, td {{ border: 1px solid var(--border); padding: 0.35rem 0.5rem; text-align: left; }}
    th {{ background: #243044; color: var(--muted); }}
    .heat {{ text-align: center; font-weight: 600; }}
    .full {{ grid-column: 1 / -1; }}
    footer {{ margin-top: 2rem; color: var(--muted); font-size: 0.75rem; }}
  </style>
</head>
<body>
  <h1>Research Benchmark Dashboard</h1>
  <p class="subtitle">B0–B3 baseline comparison · Dataset v1 · fixture-synthetic evaluation</p>
  <div class="banner">
    Classification is triage evidence — not malware attribution. Metrics are from deterministic fixtures;
    latency/recovery timing is not applicable. Do not treat as enterprise field validation.
  </div>
  <div class="meta">
    <span>Run: {escape(run_id)}</span>
    <span>Git: {escape(git_sha)}</span>
    <span>Cases: {escape(str(case_count))}</span>
    <span>Seed: {escape(str(seed))}</span>
    <span>Source: {escape(str(artifacts.results_dir))}</span>
  </div>
  <div class="grid">
    <div class="card">
      <h2>Macro F1 by baseline (95% bootstrap CI)</h2>
      <canvas id="chartF1"></canvas>
    </div>
    <div class="card">
      <h2>Accuracy by baseline</h2>
      <canvas id="chartAcc"></canvas>
    </div>
    <div class="card">
      <h2>Abstention rate</h2>
      <canvas id="chartAbs"></canvas>
    </div>
    <div class="card">
      <h2>Ablation Δ macro F1 (B3 full → ablated)</h2>
      <canvas id="chartAblation"></canvas>
    </div>
    <div class="card">
      <h2>B3 failure categories</h2>
      <canvas id="chartFail"></canvas>
    </div>
    <div class="card full">
      <h2>B3 confusion matrix (counts)</h2>
      {confusion_html}
    </div>
    <div class="card full">
      <h2>B3 misclassifications (sample)</h2>
      {failures_html}
    </div>
  </div>
  <footer>
    Generated by <code>python -m experiments.viz</code> · Regenerate via <code>make research</code> or
    <code>./scripts/reproduce.ps1</code> · Power BI tables: <code>analytics/powerbi/research/data/</code>
  </footer>
  <script>
    const DATA = {chart_payload};
    const colors = ['#64748b','#94a3b8','#6366f1','#3b82f6'];
    Chart.defaults.color = '#8b9cb3';
    Chart.defaults.borderColor = '#2d3a4f';

    new Chart(document.getElementById('chartF1'), {{
      type: 'bar',
      data: {{
        labels: DATA.baselineLabels,
        datasets: [{{
          label: 'Macro F1',
          data: DATA.macroF1,
          backgroundColor: colors,
          borderRadius: 4,
        }}]
      }},
      options: {{
        scales: {{ y: {{ min: 0, max: 1 }} }},
        plugins: {{
          tooltip: {{
            callbacks: {{
              afterLabel: (ctx) => {{
                const i = ctx.dataIndex;
                return `95% CI: ${{DATA.f1CiLower[i].toFixed(4)}} – ${{DATA.f1CiUpper[i].toFixed(4)}}`;
              }}
            }}
          }}
        }}
      }}
    }});

    new Chart(document.getElementById('chartAcc'), {{
      type: 'bar',
      data: {{ labels: DATA.baselineLabels, datasets: [{{ label: 'Accuracy', data: DATA.accuracy, backgroundColor: colors, borderRadius: 4 }}] }},
      options: {{ scales: {{ y: {{ min: 0, max: 1 }} }} }}
    }});

    new Chart(document.getElementById('chartAbs'), {{
      type: 'bar',
      data: {{ labels: DATA.baselineLabels, datasets: [{{ label: 'Abstention rate', data: DATA.abstention, backgroundColor: '#f59e0b', borderRadius: 4 }}] }},
      options: {{ scales: {{ y: {{ min: 0, max: 1 }} }} }}
    }});

    new Chart(document.getElementById('chartAblation'), {{
      type: 'bar',
      data: {{
        labels: DATA.ablationLabels,
        datasets: [{{ label: 'Δ macro F1', data: DATA.ablationDeltas, backgroundColor: DATA.ablationDeltas.map(d => d < 0 ? '#ef4444' : '#10b981'), borderRadius: 4 }}]
      }},
      options: {{ indexAxis: 'y', scales: {{ x: {{ min: -0.35, max: 0.05 }} }} }}
    }});

    new Chart(document.getElementById('chartFail'), {{
      type: 'doughnut',
      data: {{
        labels: DATA.failureLabels,
        datasets: [{{ data: DATA.failureCounts, backgroundColor: ['#ef4444','#f59e0b','#8b5cf6','#64748b'] }}]
      }},
      options: {{ plugins: {{ legend: {{ position: 'bottom' }} }} }}
    }});
  </script>
</body>
</html>
"""
    target.write_text(html, encoding="utf-8")
    return target


def _baseline_label(baseline: str) -> str:
    labels = {
        "B0": "B0 Connectivity",
        "B1": "B1 Flat rules",
        "B2": "B2 Single signal",
        "B3": "B3 Full platform",
    }
    return labels.get(baseline, baseline)


def _baseline_description(baseline: str) -> str:
    descriptions = {
        "B0": "Probe/connectivity signals only",
        "B1": "Flat if/else rules without proof tiers",
        "B2": "WinINET proxy_state single signal",
        "B3": "Evidence tiers, policy path, full classifier",
    }
    return descriptions.get(baseline, "")


def _ablation_macro_f1_deltas(ablations: list[dict[str, str]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    rows: list[dict[str, Any]] = []
    for row in ablations:
        if row.get("metric") != "macro_f1":
            continue
        key = row.get("ablation", "")
        if key in seen:
            continue
        seen.add(key)
        rows.append(
            {
                "label": f"{key} {row.get('ablation_name', '')}".strip(),
                "delta": float(row.get("absolute_delta", 0)),
            }
        )
    rows.sort(key=lambda r: r["delta"])
    return rows


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _render_confusion_table(rows: list[dict[str, str]]) -> str:
    if not rows:
        return "<p>No confusion matrix available. Run full benchmark first.</p>"
    pred_cols = [
        k for k in rows[0] if k not in {"baseline", "expected\\predicted", "expected/predicted"}
    ]
    header = (
        "<tr><th>Expected \\ Predicted</th>"
        + "".join(f"<th>{escape(c)}</th>" for c in pred_cols)
        + "</tr>"
    )
    body_rows: list[str] = []
    max_val = 1
    for row in rows:
        vals = [int(row.get(c, 0) or 0) for c in pred_cols]
        max_val = max(max_val, *vals)
        expected = row.get("expected\\predicted") or row.get("expected/predicted", "")
        cells = "".join(
            f'<td class="heat" style="background:rgba(59,130,246,{v / max_val * 0.85 if max_val else 0})">{v}</td>'
            for v in vals
        )
        body_rows.append(f"<tr><th>{escape(expected)}</th>{cells}</tr>")
    return f"<table><thead>{header}</thead><tbody>{''.join(body_rows)}</tbody></table>"


def _render_failures_table(rows: list[dict[str, str]]) -> str:
    if not rows:
        return "<p>No B3 failures recorded (perfect classification).</p>"
    header = "<tr><th>Case</th><th>Expected</th><th>Predicted</th><th>Category</th></tr>"
    body = "".join(
        f"<tr><td>{escape(r.get('case_id', ''))}</td>"
        f"<td>{escape(r.get('expected', ''))}</td>"
        f"<td>{escape(r.get('predicted', ''))}</td>"
        f"<td>{escape(r.get('failure_category', ''))}</td></tr>"
        for r in rows
    )
    return f"<table><thead>{header}</thead><tbody>{body}</tbody></table>"


def generate_all_viz(
    *,
    results_dir: Path | None = None,
    html_out: Path | None = None,
    powerbi_out: Path | None = None,
) -> dict[str, str]:
    """Generate HTML dashboard and Power BI CSV export."""
    artifacts = load_artifacts(results_dir=results_dir)
    errors = validate_artifacts(artifacts)
    if errors:
        raise FileNotFoundError("; ".join(errors))
    html_path = generate_html_dashboard(artifacts, html_out)
    pbi_path = export_powerbi_tables(artifacts, powerbi_out)
    return {"html_dashboard": str(html_path), "powerbi_export": str(pbi_path)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Research benchmark visualization")
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=None,
        help="Results directory (default: experiments/results/latest)",
    )
    parser.add_argument(
        "--html-out",
        type=Path,
        default=None,
        help="HTML dashboard output path",
    )
    parser.add_argument(
        "--powerbi-out",
        type=Path,
        default=None,
        help="Power BI CSV export directory",
    )
    parser.add_argument(
        "--open", action="store_true", help="Open HTML in default browser (Windows)"
    )
    args = parser.parse_args(argv)

    out = generate_all_viz(
        results_dir=args.results_dir,
        html_out=args.html_out,
        powerbi_out=args.powerbi_out,
    )
    print(json.dumps({"status": "ok", **out}, indent=2))

    if args.open:
        import webbrowser

        webbrowser.open(out["html_dashboard"])

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
