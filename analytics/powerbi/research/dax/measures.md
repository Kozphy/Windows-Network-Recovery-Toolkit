# DAX Measures — Research Benchmark

Use with tables in `analytics/powerbi/research/data/`.

## Core measures

```dax
Macro F1 (selected baseline) =
CALCULATE(
    MAX(fact_benchmark_metrics[metric_value]),
    fact_benchmark_metrics[metric_name] = "macro_f1"
)

B3 Macro F1 =
CALCULATE(
    MAX(fact_benchmark_metrics[metric_value]),
    fact_benchmark_metrics[baseline_key] = "B3",
    fact_benchmark_metrics[metric_name] = "macro_f1"
)

B1 Macro F1 =
CALCULATE(
    MAX(fact_benchmark_metrics[metric_value]),
    fact_benchmark_metrics[baseline_key] = "B1",
    fact_benchmark_metrics[metric_name] = "macro_f1"
)

B3 beats B1 (macro F1) =
[B3 Macro F1] > [B1 Macro F1]
```

## Bootstrap CI (macro F1, B3)

```dax
B3 Macro F1 Point =
CALCULATE(
    MAX(fact_bootstrap_ci[point_estimate]),
    fact_bootstrap_ci[baseline_key] = "B3",
    fact_bootstrap_ci[metric_name] = "macro_f1"
)

B3 Macro F1 CI Lower =
CALCULATE(
    MAX(fact_bootstrap_ci[ci_lower]),
    fact_bootstrap_ci[baseline_key] = "B3",
    fact_bootstrap_ci[metric_name] = "macro_f1"
)

B3 Macro F1 CI Upper =
CALCULATE(
    MAX(fact_bootstrap_ci[ci_upper]),
    fact_bootstrap_ci[baseline_key] = "B3",
    fact_bootstrap_ci[metric_name] = "macro_f1"
)
```

## Ablation

```dax
Ablation Macro F1 Delta =
CALCULATE(
    MAX(fact_ablations[absolute_delta]),
    fact_ablations[metric_name] = "macro_f1"
)

Total B3 Failures =
COUNTROWS(fact_b3_failures)
```

## Formatting

- Set percentage measures (`accuracy`, `macro_f1`, rates) to **Percentage** with 2 decimals in model
- Or divide by 1 if stored as 0–1 decimals (current export format)

## Limitations

- Small sample (n≈22) — avoid over-interpreting narrow CI wins
- Measures reflect **fixture replay**, not live Windows timing
