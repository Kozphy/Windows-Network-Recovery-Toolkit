# Evaluation Methodology

## 1. Baselines

Evaluate at minimum:

1. deterministic rules-only baseline;
2. Logistic Regression;
3. Random Forest;
4. boosted-tree candidates already supported by the toolkit;
5. the proposed hybrid rules + ML decision-evidence architecture.

Complexity is justified only when it produces repeatable incremental value over simpler baselines.

## 2. Data partitioning

When timestamped observations exist, use chronological train/validation/test partitions. Threshold selection, feature selection, calibration and hyperparameter selection must use training/validation data only. The test partition is evaluated after the protocol is frozen.

If temporal data is unavailable, clearly label stratified random splitting as a limitation rather than treating it as equivalent evidence.

## 3. Metrics

Report:

- precision and recall;
- F1;
- false-positive and false-negative rates;
- ROC-AUC;
- PR-AUC;
- Brier score;
- expected calibration error when calibration experiments are enabled;
- sample counts and class prevalence.

Operational thresholds must be reported with the metrics they produce.

## 4. Calibration

Raw classifier probabilities must not be described as calibrated. Compare uncalibrated probabilities with an explicit calibration method fitted without test leakage. Report reliability/calibration results alongside discrimination metrics.

## 5. Uncertainty

Use bootstrap resampling or another documented method to report confidence intervals for headline metrics. Record random seeds and resampling configuration.

## 6. Ablation

Remove coherent feature/control groups from the full system and rerun the frozen evaluation. Examples include proxy evidence, DNS/TLS signals, reset history, network profile and deterministic-control evidence.

## 7. Failure analysis

Review false positives and false negatives by the taxonomy in `failure_taxonomy.md`. Do not treat aggregate F1 as sufficient evidence of operational safety.

## 8. Reproducibility

Each benchmark result should preserve:

- dataset/version identifier;
- commit SHA;
- experiment configuration;
- dependency/runtime information;
- random seed;
- generated metrics;
- evaluation timestamp.

## 9. Threats to validity

Explicitly discuss construct validity (does `failure_label` represent the intended risk?), internal validity (leakage/confounding), external validity (environment coverage) and statistical conclusion validity (sample size/uncertainty).