# Methodology

## Primary hypothesis

A deterministic classifier that fuses WinINET, WinHTTP, listener/process, TLS-path, and policy evidence will produce fewer unsafe false-positive remediation recommendations than simpler single-signal or rule-only baselines.

## Experimental unit

One incident fixture represents one endpoint observation window. Each fixture should contain:

- observed network/proxy/TLS evidence
- ground-truth incident label
- expected proof tier
- expected safety posture (`ALLOW`, `PREVIEW`, or `BLOCK`)
- provenance and fixture revision

## Dataset partitions

Use deterministic train-free evaluation partitions because the primary classifier is rule/state-machine based:

- `canonical`: known representative incidents
- `edge_cases`: missing, stale, conflicting, duplicated, and malformed evidence
- `stress`: large synthetic fleets generated from fixed seeds
- `holdout`: fixtures not used while authoring classifier rules

Never report synthetic data as real-world production evidence.

## Metrics

### Classification

- accuracy
- per-class precision and recall
- macro F1
- confusion matrix
- abstention rate

### Safety

- false-positive remediation rate: cases where an unsafe or unnecessary remediation would be recommended
- false-negative block rate: cases where a justified remediation is incorrectly blocked
- proof-tier mismatch rate
- policy-gate violation count (target: zero)

### Systems

- classification latency p50/p95/p99
- throughput at fixed fleet sizes
- deterministic replay mismatch count (target: zero for identical inputs/version)

## Comparison protocol

For every fixture, run the same immutable input through:

1. baseline A: single-signal proxy heuristic
2. baseline B: multi-rule heuristic without proof tiers
3. full evidence-tier classifier

Record all outputs in machine-readable JSONL. A result is valid only when classifier version, fixture revision, random seed, and environment metadata are captured.

## Statistical reporting

Where sample size permits, report bootstrap 95% confidence intervals for aggregate accuracy/F1 and paired differences between methods. For small curated fixture sets, report exact counts and avoid overstating statistical significance.

## Robustness experiments

Evaluate the full classifier after introducing one controlled perturbation at a time:

- remove WinINET evidence
- remove WinHTTP evidence
- remove listener/process evidence
- remove TLS-path evidence
- duplicate an event
- reorder events
- mark one source stale
- inject contradictory evidence

The desired behavior is not always a correct positive classification; safe abstention with explicit `limitations[]` is considered a valid outcome.

## Threats to validity

- fixture labels may encode author assumptions
- synthetic incident distributions may not match enterprise fleets
- ordinal confidence values are not calibrated probabilities
- deterministic rules may overfit known Windows failure modes
- system latency measured locally does not imply cloud or enterprise performance

## Claim discipline

Results may support statements such as "reduced false-positive remediation recommendations on the evaluated fixture set." They must not be generalized into claims of universal reliability, security compromise detection, formal audit assurance, or production-scale validation without corresponding evidence.
