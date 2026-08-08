# Baselines

The research layer needs explicit comparison systems. These baselines are intentionally simpler than the production-shaped classifier and must be evaluated on the same immutable fixtures.

## Baseline A — Single-signal proxy heuristic

Decision logic uses only the configured proxy endpoint and whether a corresponding local listener exists.

Example policy:

- proxy disabled -> `NO_PROXY_FAILURE`
- proxy enabled + listener present -> `PROXY_PRESENT`
- proxy enabled + listener absent -> `DEAD_PROXY_CONFIG`

This baseline ignores WinINET/WinHTTP drift, TLS-path evidence, provenance, proof tiers, contradictory evidence, and policy context.

## Baseline B — Multi-rule heuristic without proof tiers

Uses multiple evidence sources but returns the first matching incident rule. It has no explicit T0-T5 proof tier, no abstention model, and no structured `limitations[]` semantics.

This isolates the value of proof-aware decision logic from the value of merely adding more rules.

## Full system

The full system is the repository's deterministic evidence-tier classifier with:

- multi-source evidence
- explicit proof tiers
- limitations and uncertainty disclosure
- state-aware classification
- policy-gated remediation preview
- deterministic replay and audit output

## Fair-comparison requirements

All methods must receive the same fixture revision. Do not give the full system additional ground-truth metadata. Report both classification quality and safety outcomes; a method that increases nominal accuracy while increasing unsafe remediation recommendations is not superior.

## Minimum comparison table

| Method | Accuracy | Macro F1 | False-positive remediation rate | Abstention rate | p95 latency |
|---|---:|---:|---:|---:|---:|
| Baseline A | TBD | TBD | TBD | TBD | TBD |
| Baseline B | TBD | TBD | TBD | TBD | TBD |
| Full evidence-tier classifier | TBD | TBD | TBD | TBD | TBD |

`TBD` is intentional. Do not populate results until they are generated from a reproducible experiment run.
