# Research Questions and Hypotheses

## RQ1 — Predictive value

**Question:** Does predictive ML improve endpoint-risk detection over deterministic controls?

**H1:** At an operating threshold selected without test-set leakage, the best validated ML model improves PR-AUC and/or F1 over the rules-only baseline without an unacceptable increase in false-positive rate.

## RQ2 — Hybrid decision evidence

**Question:** Does combining deterministic control evidence with predictive ML improve operational triage?

**H2:** The hybrid approach reduces false positives relative to a high-recall rules-only baseline while preserving operationally acceptable recall.

## RQ3 — Probability quality

**Question:** Are model probabilities calibrated well enough to support governance thresholds?

**H3:** Explicit post-hoc calibration improves Brier score and expected calibration error on validation/temporal holdout data relative to raw model probabilities.

## Secondary questions

- How does performance change under temporal distribution shift?
- Which feature/control groups account for most incremental value?
- Which failure classes dominate false positives and false negatives?
- How stable are conclusions under bootstrap resampling and alternate seeds?

## Claim discipline

Results from synthetic or demonstrative sample data are engineering validation only. Production or research-performance claims require documented, appropriately labeled telemetry and a frozen evaluation protocol.