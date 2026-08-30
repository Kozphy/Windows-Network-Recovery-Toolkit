# Optional Model-Risk Analytics

This layer adds governed incident-review prioritization without changing the deterministic evidence, control-testing, policy, or remediation paths.

## Install

```bash
pip install -e ".[ml]"
```

The base project does not require PyTorch. Without the `ml` extra, the deterministic recurrence baseline remains available and importing `src.platform_core.model_risk` still works.

## Intended use

- rank incidents for human review;
- compare deterministic and learned models;
- experiment with recurrence-risk features;
- demonstrate model governance, validation, and model-card practices.

## Not intended for

- authorizing remediation;
- replacing control-test conclusions;
- declaring causation, compromise, or malware;
- producing an audit opinion;
- treating a score as a calibrated probability without validation.

## Feature contract

`RiskFeatures` uses a stable ten-column vector derived from evidence, control tests, and outcomes:

1. proxy enabled;
2. corroborating listener found;
3. direct probe result;
4. proxy probe result;
5. proof tier;
6. failed control count;
7. partial control count;
8. recurrence count;
9. previous restoration independently verified;
10. time to restoration.

Missing probe results use an explicit sentinel rather than being inferred.

## Models

### Deterministic baseline

`deterministic_recurrence_score` is transparent, bounded, and available in the base installation. It produces reasons for each contribution and labels the result as a heuristic rather than a probability.

### PyTorch MLP

`RecurrenceRiskMLP` is a small tabular neural network for experimentation. A model must not be promoted beyond development without:

- versioned training data and dataset hash;
- holdout evaluation and class-balance reporting;
- threshold rationale;
- calibration analysis;
- drift monitoring;
- approved model card;
- rollback plan;
- named owner and reviewer.

## Governance invariant

Every `ModelRecommendation` has:

```text
execution_authority = NONE
human_review_required = true
```

A model score can prioritize review. It cannot mutate proxy settings, kill processes, bypass policy gates, or upgrade an evidence tier.
