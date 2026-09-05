# Research Benchmark Report Blueprint (Power BI)

**Data source:** `analytics/powerbi/research/data/` (from `python -m experiments.viz`)
**Audience:** Research reviewers, data science hiring managers, risk analytics portfolio

---

## Page 1: Baseline Comparison

| Visual | Fields |
|--------|--------|
| **Clustered bar** | Axis: `dim_baseline[baseline_name]` · Value: `macro_f1` measure (filter `metric_name = "macro_f1"`) |
| **Clustered bar** | Same for `accuracy` |
| **Cards** | Sample size, git SHA (from manifest or first row), case count |
| **Table** | All metrics by baseline from `fact_benchmark_metrics` |

**Slicers:** `baseline_key`, `metric_name`

**Narrative:** B3 full platform vs simpler baselines on fixture dataset v1. Wide bootstrap CIs reflect small n=22 — exploratory, not confirmatory.

---

## Page 2: Statistical Uncertainty

| Visual | Fields |
|--------|--------|
| **Clustered bar + error bars** | `fact_bootstrap_ci` where `metric_name = "macro_f1"`: Y = `point_estimate`, Error lower = `point_estimate - ci_lower`, Error upper = `ci_upper - point_estimate` |
| **Line chart** | `metric_name` × `point_estimate` for B3 only (accuracy, macro_f1, abstention_rate) |
| **Table** | Full CI table with `n_bootstrap`, `random_seed` |

**Footer:** IID case resampling assumption; not enterprise-scale inference.

---

## Page 3: Ablation Study

| Visual | Fields |
|--------|--------|
| **Waterfall or bar** | Filter `metric_name = "macro_f1"`: X = `ablation_key`, Y = `absolute_delta` |
| **Matrix** | Rows: `ablation_key` · Columns: `metric_name` · Values: `absolute_delta` |
| **Table** | Top negative deltas with `notes` |

**Narrative:** Each ablation answers “what measurable contribution does this component make?” Negative delta = removing component hurts macro F1.

---

## Page 4: Failure Analysis (B3)

| Visual | Fields |
|--------|--------|
| **Donut** | `failure_category` count from `fact_b3_failures` |
| **Table** | `case_id`, `expected_class`, `predicted_class`, `failure_category`, `proof_tier` |
| **Matrix heatmap** | `fact_confusion_matrix_b3`: rows = `expected_class`, cols = `predicted_class`, values = `count` |

**Slicers:** `failure_category`, `ambiguity_allowed`

**Narrative:** Negative evidence is valuable — insufficient_evidence and cross_signal_interaction are expected on ambiguous fixtures.

---

## Recommended theme

- Dark header matching HTML dashboard (`#1a2332`)
- Disclaimer text box on every page: *Fixture-synthetic evaluation · Classification ≠ accusation*
- Do not label visuals “Malware detected” or “Production MTTR”

---

## Regenerate data

```powershell
make research
python -m experiments.viz
```

Never hand-edit CSV metric cells — refresh from benchmark run.
