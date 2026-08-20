# Hypotheses

## H1 — Drift detection effectiveness

**Hypothesis:** Multi-source reconciliation using WinINET, WinHTTP, listener/path evidence, and explicit state transitions achieves higher macro-F1 for proxy-drift incident classification than a WinINET-only baseline on the frozen evaluation set.

**Reject support for H1 if:** the 95% bootstrap confidence interval for the macro-F1 difference includes zero, or the multi-source system performs worse on any pre-declared critical safety class.

## H2 — False-positive control

**Hypothesis:** Multi-source reconciliation reduces false positive drift alerts relative to a single-source baseline without reducing recall by more than 2 percentage points.

**Reject support for H2 if:** false-positive rate does not improve, or recall degradation exceeds the tolerance.

## H3 — Deterministic replay

**Hypothesis:** Identical frozen inputs, configuration, seed, and code revision yield byte-identical normalized classification outputs across repeated runs.

**Reject support for H3 if:** any unexplained output divergence appears across 10 repeated runs.

## H4 — Explainability completeness

**Hypothesis:** Every evaluated classification contains an incident label, evidence tier, contributing evidence, and explicit limitations.

**Reject support for H4 if:** completeness is below 100% for the frozen evaluation set.

## H5 — Safety preservation

**Hypothesis:** Research-mode evaluation never authorizes autonomous remediation and does not emit malware/compromise verdicts from proxy reliability evidence.

**Reject support for H5 if:** any evaluation path violates existing safety contracts.

## Null hypothesis discipline

A null or negative result is a valid outcome. Results must not be reframed after evaluation by changing metrics, classes, thresholds, or exclusions without recording a new protocol version.
