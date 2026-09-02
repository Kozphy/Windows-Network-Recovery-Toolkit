# Research Benchmark — Power BI Template

Power BI import for **B0–B3 classification benchmark**, bootstrap CIs, ablations, and B3 failure analysis.

> **Honest scope:** Fixture-synthetic dataset v1 — not enterprise field validation. Classification is triage evidence, not malware attribution.

## Generate CSV tables

```powershell
$env:PYTHONPATH = (Get-Location).Path
python -m experiments.run_benchmark          # if artifacts missing
python -m experiments.viz                    # exports CSVs + HTML dashboard
```

Or as part of full pipeline:

```powershell
make research
```

**Export location:** `analytics/powerbi/research/data/`

| File | Role |
|------|------|
| `dim_baseline.csv` | B0–B3 dimension |
| `fact_benchmark_metrics.csv` | Long-format headline metrics |
| `fact_bootstrap_ci.csv` | 95% bootstrap intervals |
| `fact_ablations.csv` | A1–A7 component deltas |
| `fact_b3_failures.csv` | B3 misclassification rows |
| `fact_confusion_matrix_b3.csv` | Confusion matrix (long format) |
| `manifest.json` | Run metadata pointer |

## Import into Power BI Desktop

1. **Get data** → Text/CSV → select all files in `analytics/powerbi/research/data/`
2. **Relationships** (Model view):

   | From | To | Cardinality |
   |------|-----|-------------|
   | `fact_benchmark_metrics[baseline_key]` | `dim_baseline[baseline_key]` | Many → One |
   | `fact_bootstrap_ci[baseline_key]` | `dim_baseline[baseline_key]` | Many → One |
   | `fact_ablations` | (standalone facts) | — |
   | `fact_b3_failures` | (standalone) | — |
   | `fact_confusion_matrix_b3[baseline_key]` | `dim_baseline[baseline_key]` | Many → One |

3. Set `metric_value`, `point_estimate`, `absolute_delta`, `count` to **Decimal Number**
4. Build pages per [report_blueprint.md](report_blueprint.md)
5. Add DAX from [dax/measures.md](dax/measures.md)

## HTML alternative (no Power BI license)

Open [`benchmarks/reports/research_dashboard.html`](../../../benchmarks/reports/research_dashboard.html) in a browser after `python -m experiments.viz`.

## Related

- [REPRODUCING.md](../../../REPRODUCING.md)
- [Enterprise Power BI layer](../README.md)
- [Research gap analysis](../../../docs/research/GAP_ANALYSIS.md)
