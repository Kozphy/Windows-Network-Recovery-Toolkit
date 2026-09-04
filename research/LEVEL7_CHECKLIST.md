# Level 7 Research-Grade Exit Checklist

Level 7 is earned through reproducible empirical evidence, not repository size or model count.

## Implemented in the research stack

- [x] Explicit research questions and falsifiable hypotheses
- [x] Dataset card and claim-discipline template
- [x] Strict temporal holdout support
- [x] Logistic-regression baseline
- [x] Random-forest baseline
- [x] Deterministic rules-only comparator on the same holdout rows
- [x] Optional sigmoid/Platt probability calibration
- [x] Brier score
- [x] Expected Calibration Error (ECE)
- [x] Reliability-bin output
- [x] Deterministic bootstrap confidence interval for F1
- [x] Paired bootstrap F1-delta comparison against rules-only baseline
- [x] Proxy/TLS/DNS feature-group ablations
- [x] Machine-readable JSON/CSV benchmark artifacts
- [x] Regression tests for temporal split, ablations, metrics, bootstrap CI, rules baseline, calibration diagnostics, and paired comparison
- [x] Failure taxonomy schema

## Evidence gates still required before claiming full Level 7

- [ ] Versioned labeled telemetry dataset with documented provenance
- [ ] Explicit label-generation/adjudication procedure populated with real evidence
- [ ] Benchmark results generated from that dataset and committed or attached as immutable artifacts
- [ ] Observed false-positive and false-negative cases populated in the failure taxonomy
- [ ] Cross-environment or cross-device validation where data permits
- [ ] Clean-environment reproduction through CI or a documented container/lockfile path
- [ ] Review of leakage risks and confirmation that no future information enters training features
- [ ] Review of calibration stability under temporal drift
- [ ] Research conclusions updated to distinguish supported findings from hypotheses

## Claim discipline

Until the evidence gates above are complete, describe the project as:

> An advanced full-stack technology-risk platform with a research-grade evaluation framework in active validation.

Do **not** describe synthetic/demo benchmark output as production performance or real-world effectiveness.
