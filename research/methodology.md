# Research Methodology

## Evaluation goal

Determine whether predictive models add measurable value over deterministic Windows/network controls without overstating evidence quality.

## Primary protocol

Use a strict temporal holdout whenever timestamps are available:

1. Sort observations by time.
2. Train only on the earlier window.
3. Evaluate once on the later holdout window.
4. Never tune against the final holdout.

This approximates the real deployment direction: past evidence is used to predict future outcomes.

## Baselines

The research stack compares:

- deterministic rules-only evidence on the same holdout rows
- logistic regression
- random forest
- optional calibrated versions of supervised models
- richer models may be added only when they answer a specific research question

The rules comparator intentionally stays simple. It is a fixed reference point rather than a tuned replacement for the toolkit control engine.

## Metrics

Report at minimum:

- accuracy
- precision
- recall
- F1
- ROC-AUC when both classes exist in the holdout
- PR-AUC when both classes exist in the holdout
- Brier score
- Expected Calibration Error (ECE)
- reliability-bin statistics

Threshold-dependent metrics use a documented threshold, currently 0.5 in the benchmark runner unless a future experiment explicitly defines otherwise.

## Calibration

A probabilistic classifier is not automatically a calibrated risk model.

The runner supports sigmoid/Platt calibration through `CalibratedClassifierCV` and separately reports Brier score, ECE, and reliability bins. Calibration quality must be re-evaluated when time, environment, or endpoint population changes.

## Uncertainty

Use deterministic percentile bootstrap intervals for F1 to quantify sampling uncertainty. The default benchmark uses 1,000 resamples with a fixed seed for reproducibility.

## Paired comparison

When comparing ML with deterministic controls, resample the same holdout rows for both systems. Report the bootstrap distribution of:

`F1(candidate) - F1(rules_only)`

The benchmark records the median delta, confidence interval, and fraction of bootstrap samples where the candidate is better. An interval excluding zero is stronger evidence than a raw point-estimate difference, but it is not proof of cross-environment generalization.

## Ablation

Remove feature groups such as proxy, TLS, and DNS signals while holding the evaluation window constant. Use ablation evidence to identify whether a feature/control group contributes measurable value rather than assuming every engineered feature is useful.

## Failure analysis

For observed errors, classify at least:

- false positive
- false negative
- data-quality failure
- configuration drift
- feature extraction failure
- model failure
- policy failure
- remediation failure
- verification failure

## Reproducibility

Each reported result should preserve:

- dataset version/provenance
- collection window
- label definition
- feature schema
- code commit
- random seed
- command/configuration
- generated JSON/CSV artifacts
- limitations and threats to validity

Synthetic or demo data may verify software execution but must never be presented as evidence of production effectiveness.
