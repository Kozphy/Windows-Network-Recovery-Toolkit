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

## Executable benchmark

`run_benchmark.py` implements the first executable Level-7 evaluation path:

- strict past-to-future temporal holdout using `observed_at` (configurable)
- logistic-regression and random-forest baselines
- optional sigmoid/Platt probability calibration
- deterministic bootstrap confidence interval for F1
- feature-group ablations for proxy, TLS and DNS signals when those groups exist
- machine-readable JSON and CSV result artifacts
- explicit guardrails separating demo/synthetic evidence from production claims

Example:

```bash
python research/run_benchmark.py \
  --data path/to/labeled_telemetry.csv \
  --timestamp-column observed_at \
  --calibrate \
  --bootstrap-iterations 1000 \
  --out research/results/latest
```

Expected outputs:

```text
research/results/latest/
├── benchmark.json
└── benchmark.csv
```

A valid research dataset must contain `failure_label` with both binary classes and a timestamp column. The training window must itself contain both classes. Do not use synthetic/demo output as evidence of real-world effectiveness.

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

The executable benchmark foundation is now present, but **Level 7 is not claimed complete until it is run against a documented labeled telemetry dataset and the resulting evidence is reviewed**. Remaining high-value work includes a rules-only baseline, explicit calibration-error/reliability reporting, cross-environment validation, richer statistical comparisons, and versioned real telemetry.

## Structure

```text
research/
├── README.md
├── questions.md
├── methodology.md
├── dataset_card.md
├── run_benchmark.py
├── experiments/
├── results/
└── failure_taxonomy.md
```
