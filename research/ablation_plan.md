# Ablation Plan

Ablation experiments test which parts of the evidence model actually contribute to decision quality.

## Evidence-source ablations

Run the complete evaluation suite with exactly one source removed at a time:

1. no WinINET evidence
2. no WinHTTP evidence
3. no listener/process evidence
4. no TLS-path evidence
5. no provenance/freshness metadata

Measure delta in macro F1, false-positive remediation rate, abstention rate, and proof-tier mismatch rate relative to the full classifier.

## Decision-model ablations

1. remove proof tiers but keep all evidence
2. remove `limitations[]`-driven abstention behavior
3. collapse state-machine transitions into stateless rules
4. remove policy gating from evaluation output (preview only; never execute remediation)

## Robustness ablations

Perturb one dimension at a time:

- stale evidence
- contradictory sources
- event duplication
- event reordering
- partial source loss
- malformed optional fields

## Interpretation

An ablation is useful when it explains *why* the system works. A component that changes no meaningful metric may be unnecessary complexity. A component that slightly reduces raw accuracy but materially reduces unsafe remediation recommendations may still be valuable because safety is a first-class objective.

## Reporting template

| Ablation | Macro F1 Δ | False-positive remediation Δ | Abstention Δ | Interpretation |
|---|---:|---:|---:|---|
| Full system | 0 | 0 | 0 | Reference |
| No WinINET | TBD | TBD | TBD | TBD |
| No WinHTTP | TBD | TBD | TBD | TBD |
| No listener/process | TBD | TBD | TBD | TBD |
| No TLS path | TBD | TBD | TBD | TBD |
| No proof tiers | TBD | TBD | TBD | TBD |

Do not fill `TBD` values manually; populate them from experiment artifacts.
