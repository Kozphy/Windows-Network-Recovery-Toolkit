# Research-Grade Technology Risk Evaluation

This directory defines the Level-7 research contract for the Windows Network Recovery Toolkit.

## Objective

Move from a demonstrable ML prototype to a reproducible experimental platform. Claims must be backed by labeled evidence and repeatable evaluation; sample data must never be presented as production performance.

## Research questions

- **RQ1:** Does predictive ML improve endpoint-risk detection over deterministic controls?
- **RQ2:** Does a hybrid rules + ML approach reduce false positives while preserving recall?
- **RQ3:** Are predicted probabilities sufficiently calibrated to support policy thresholds?

## Executable benchmark

`run_benchmark.py` now provides a stronger Level-7 evidence path:

- strict past-to-future temporal holdout using `observed_at` (configurable)
- deterministic rules-only comparator evaluated on the same holdout rows
- logistic-regression and random-forest supervised baselines
- optional sigmoid/Platt probability calibration
- Brier score, Expected Calibration Error (ECE), and reliability-bin output
- deterministic bootstrap confidence interval for F1
- paired bootstrap F1-delta comparison between each ML model and the rules baseline
- proxy/TLS/DNS feature-group ablations
- machine-readable JSON and CSV result artifacts
- explicit guardrails separating demo/synthetic evidence from production claims

Example:

```bash
python research/run_benchmark.py \
  --data path/to/labeled_telemetry.csv \
  --timestamp-column observed_at \
  --calibrate \
  --bootstrap-iterations 1000 \
  --calibration-bins 10 \
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
9. Treat probability calibration as an empirical property to be measured, not a label inferred from having a probabilistic model.
10. Prefer paired comparisons on the same holdout rows when comparing models with deterministic controls.

## Level-7 exit criteria

A reviewer should be able to clone the repository, obtain or generate the documented dataset, run the benchmark, reproduce the reported tables, inspect limitations, and distinguish demonstrated results from future claims.

The executable benchmark foundation now includes temporal validation, rules-only comparison, calibration diagnostics, uncertainty intervals, paired bootstrap comparison, and ablation support. **Level 7 is still not claimed complete until this framework is run against a documented versioned labeled telemetry dataset and the resulting evidence is reviewed.** Remaining gates are tracked in `LEVEL7_CHECKLIST.md`.

## Structure

```text
research/
├── README.md
├── questions.md
├── methodology.md
├── dataset_card.md
├── failure_taxonomy.md
├── LEVEL7_CHECKLIST.md
├── run_benchmark.py
├── experiments/
└── results/
```
