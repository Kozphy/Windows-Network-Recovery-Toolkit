# Robustness and Distribution-Shift Protocol

## Objective

Test whether conclusions from the primary benchmark remain defensible when evidence quality or scenario distribution changes. This protocol should be frozen before inspecting final robustness results.

## Shift families

### S1 — Missing evidence
Remove one or more evidence families according to prespecified missingness patterns.

### S2 — Contradictory evidence
Construct cases where otherwise credible sources disagree, including WinINET/WinHTTP and configuration/connectivity disagreement.

### S3 — Temporal ambiguity
Increase transient failures and recovery cases so a single snapshot is less informative.

### S4 — Prevalence shift
Change the relative frequency of normal, persistent-drift, and transient-failure scenarios without changing detector code.

### S5 — Measurement noise
Introduce bounded, documented perturbations to non-ground-truth observations where technically meaningful.

### S6 — Novel combinations
Combine evidence states not present in development scenarios while remaining plausible under the domain model.

### S7 — Environment variation
Where reproducible infrastructure permits, evaluate prespecified Windows/runtime/configuration differences and record the exact environment.

## Controls

For every shift experiment:

- freeze detector code before final run;
- use identical metric definitions across methods;
- evaluate B0–B3 and relevant ablations on the same cases;
- retain raw predictions;
- record seeds for synthetic perturbations;
- do not silently discard failed or ambiguous cases;
- report coverage/abstention as well as classification metrics.

## Primary robustness outcomes

1. change in macro-F1 from in-distribution benchmark;
2. change in false-remediation rate;
3. change in automated-intervention coverage;
4. contradiction-specific false-remediation rate;
5. calibration degradation if calibrated probabilities are implemented.

## Stress-test interpretation

Robustness is not binary. Report degradation curves where possible. A method that degrades gracefully may be preferable to one with a higher in-distribution score but catastrophic shift behavior.

## Negative-result policy

A failed robustness test is a research result. Do not tune against the final robustness set and then report the same set as independent evidence. Any post-hoc fix creates a new method version requiring a new held-out evaluation.

## Result table template

| Shift | Method | Macro-F1 | Δ F1 | False remediation | Coverage | Notes |
|---|---|---:|---:|---:|---:|---|
| ID | B0 | TBD | TBD | TBD | TBD | TBD |
| ID | B1 | TBD | TBD | TBD | TBD | TBD |
| ID | B2 | TBD | TBD | TBD | TBD | TBD |
| ID | B3 | TBD | TBD | TBD | TBD | TBD |

## Research question

The final discussion should answer not merely "does performance fall?" but:

> Which assumptions about evidence quality and scenario distribution are necessary for the intervention policy to remain defensible?
