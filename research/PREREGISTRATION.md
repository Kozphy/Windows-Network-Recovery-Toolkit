# Experimental Preregistration

Status: **DRAFT — freeze before final test evaluation**

This file exists to reduce hindsight bias and test-set tuning. Fill in all `TBD` fields and commit the frozen version before running the final evaluation.

## Study title

Evidence Sufficiency for Safe Endpoint Remediation under Configuration Drift

## Primary research question

Does multi-source endpoint evidence reduce false remediation decisions relative to simpler evidence baselines on a held-out benchmark?

## Primary hypothesis

H1: B3 full evidence fusion has a lower false-remediation rate than B0–B2 on the frozen test benchmark.

## Secondary hypotheses

- H2: An abstention policy reduces false remediation while increasing review rate.
- H3: Removing temporal evidence degrades persistent-vs-transient discrimination.
- H4: Under held-out distribution shifts, abstention reduces unsafe forced decisions.

## Primary outcome

**False remediation rate**

Definition: `incorrect remediation recommendations / all remediation recommendations`.

Exact mapping from classifier output to a remediation recommendation: `TBD`.

## Secondary outcomes

- macro-F1
- per-class precision and recall
- abstention rate
- human-review rate
- persistent-fault miss rate

## Benchmark

Benchmark version: `TBD`

Development cases: `TBD`

Validation cases: `TBD`

Final test cases: `TBD`

Split unit (case/scenario/provenance group): `TBD`

Ground-truth procedure: `TBD`

Exclusion criteria decided before test evaluation: `TBD`

## Methods

- B0 Registry-only
- B1 WinINET-only
- B2 WinHTTP + registry
- B3 Full evidence fusion

Exact commit implementing methods: `TBD`

## Threshold selection

All thresholds must be selected using development/validation data only.

Selection rule: `TBD`

No threshold may be changed after inspecting final test labels/results unless the original result remains reported and the change is explicitly labeled post-hoc.

## Statistical analysis

Bootstrap repetitions: `TBD` (recommended >= 2000 where computationally practical)

Confidence level: 95%

Comparison design: paired bootstrap over identical test cases where applicable.

Random seed(s): `TBD`

## Ablations

Pre-specified:

- B3 - temporal
- B3 - TLS
- B3 - WinHTTP
- B3 - connectivity
- B3 - cross-source consistency

## Distribution-shift tests

Pre-specified:

- increased transient-failure prevalence
- missing TLS evidence
- missing WinHTTP evidence
- unseen proxy-state combinations
- noisy temporal evidence

Exact generation procedure: `TBD`

## Decision-cost sensitivity

If asymmetric decision costs are reported, evaluate a predeclared range rather than a single favorable value.

`C_FP` range: `TBD`

`C_FN` range: `TBD`

`C_A` range: `TBD`

## Stopping rule

Final benchmark size/stopping rule: `TBD`

Do not add cases selectively because they improve the preferred method. New cases discovered after the freeze belong to a new benchmark version and must be reported separately.

## Deviations

After freezing this preregistration, document every deviation below rather than silently editing the original plan.

| Date | Deviation | Reason | Impact |
|---|---|---|---|
| — | — | — | — |
