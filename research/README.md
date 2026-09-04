# Research-Grade Technology Risk Evaluation

This directory defines the Level-7 research contract for the Windows Network Recovery Toolkit.

## Objective

Move from a demonstrable ML prototype to a reproducible experimental platform. Claims must be backed by labeled evidence and repeatable evaluation; sample data must never be presented as production performance.

## Research questions

- **RQ1:** Does predictive ML improve endpoint-risk detection over deterministic controls?
- **RQ2:** Does a hybrid rules + ML approach reduce false positives while preserving recall?
- **RQ3:** Are predicted probabilities sufficiently calibrated to support policy thresholds?

## Required evaluation

Report precision, recall, F1, false-positive rate, ROC-AUC, PR-AUC, Brier score and calibration error. Prefer temporal holdout evaluation when timestamps are available. Report uncertainty with bootstrap confidence intervals and compare the full system against simpler baselines.

## Experimental contract

1. Record dataset provenance and labeling rules in `dataset_card.md`.
2. Freeze the feature schema and target definition for each experiment.
3. Keep train/validation/test boundaries explicit; never tune against the test set.
4. Use deterministic seeds where supported.
5. Compare rules-only and simple statistical baselines before complex models.
6. Run ablations to identify which feature/control groups create measurable value.
7. Preserve metrics and configuration artifacts required to reproduce a result.
8. Document false positives, false negatives, data-quality failures and drift failures.

## Level-7 exit criteria

A reviewer should be able to clone the repository, obtain or generate the documented dataset, run the benchmark, reproduce the reported tables, inspect limitations, and distinguish demonstrated results from future claims.

## Planned structure

```text
research/
├── README.md
├── questions.md
├── methodology.md
├── dataset_card.md
├── experiments/
├── results/
└── failure_taxonomy.md
```

The next implementation milestone is a one-command benchmark runner with temporal validation, calibration, bootstrap confidence intervals and ablation support.