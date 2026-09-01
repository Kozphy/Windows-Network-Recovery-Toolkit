# Technical Report — Evidence-Tiered Endpoint Diagnosis Benchmark

## Abstract

Under controlled fixture benchmark dataset v1, we compare connectivity-only (B0),
flat-rule (B1), single-signal WinINET (B2), and full platform (B3) baselines.
All numerical claims below originate from generated artifacts in this repository.

## Research Question

Can deterministic, evidence-tiered endpoint diagnosis improve classification quality,
auditability, safety, and decision reproducibility compared with simpler troubleshooting baselines?

## Dataset

- Version: v1
- Cases: 22
- Git SHA: `95bad4ce215d1b75f562a8c4f7a50a1bbca471db`
- Run ID: `20260901T151326Z`

## Baseline Results (classification)

| Baseline | Accuracy | Macro F1 | Abstention rate | Exact matches |
|----------|----------|----------|-----------------|---------------|
| B0 | 0.1364 | 0.0868 | 0.6818 | 3 |
| B1 | 0.4545 | 0.4233 | 0.0000 | 10 |
| B2 | 0.1364 | 0.0583 | 0.4091 | 3 |
| B3 | 0.6364 | 0.5852 | 0.3636 | 14 |

## Statistical Analysis (bootstrap 95% CI)

| Metric | Baseline | Point | CI lower | CI upper | n |
|--------|----------|-------|----------|----------|---|
| accuracy | B3 | 0.6364 | 0.4091 | 0.8182 | 22 |
| macro_f1 | B3 | 0.5852 | 0.4464 | 0.7619 | 22 |
| abstention_rate | B3 | 0.3636 | 0.1818 | 0.5909 | 22 |

## Reproducibility

- **repeats**: 3
- **digest_agreement**: True
- **classification_agreement_rate**: 1.0
- **proof_tier_agreement_rate**: 1.0
- **policy_decision_agreement_rate**: 1.0
- **replay_mismatch_count**: 0

## Ablation Study (selected B3 deltas)

- **A1** (remove_proof_tiers): macro_f1 0.5852 → 0.5852 (Δ 0.0000)
- **A2** (remove_listener_process): macro_f1 0.5852 → 0.4550 (Δ -0.1302)
- **A3** (remove_tls_path): macro_f1 0.5852 → 0.3295 (Δ -0.2557)
- **A4** (remove_limitations): macro_f1 0.5852 → 0.5852 (Δ 0.0000)
- **A5** (remove_policy_gate): macro_f1 0.5852 → 0.5852 (Δ 0.0000)
- **A6** (remove_hash_chain): macro_f1 0.5852 → 0.5852 (Δ 0.0000)
- **A7** (remove_cross_signal_aggregation): macro_f1 0.5852 → 0.4233 (Δ -0.1619)

## Error Analysis (B3 failures)

Total B3 misclassifications: **8**
- insufficient_evidence: 7
- cross_signal_interaction: 1

## Limitations

- Fixture-synthetic evidence only; external validity to live enterprise endpoints is limited.
- Macro metrics prioritized due to class imbalance.
- Policy/safety metrics are synthetic governance checks, not proof of real-world safety.

## Reproducibility

```powershell
$env:PYTHONPATH = (Get-Location).Path
python -m experiments.run_all
```

Artifacts:
- `experiments/results/20260901T151326Z/metrics.csv`
- `benchmarks/statistical_summary.csv`
- `benchmarks/ablations.csv`
- `benchmarks/error_analysis.csv`
