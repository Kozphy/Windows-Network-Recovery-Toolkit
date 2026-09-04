# Paper outline — Evidence-Based Endpoint Risk and Decision System

> Structural skeleton only. **Do not invent citations or experimental numbers.**
> Insert measured results from `benchmarks/` and `experiments/results/` after a frozen run.

## Title (working)

Evidence-Based Diagnosis of Windows Endpoint Network Failures: A Reproducible Benchmark Against Rule, Heuristic, and Classical ML Baselines

## Abstract

TODO: one paragraph summarizing problem, method, offline fixture evaluation, and limitations.
Results will be inserted automatically from the reproducible experiment pipeline.

## 1. Introduction

- Windows endpoints can fail application paths while basic connectivity appears healthy.
- Ad-hoc remediation lacks proof tiers, auditability, and comparable evaluation.
- Contribution: shared benchmark, baselines, proposed evidence-tiered system, ablations, uncertainty reporting.

## 2. Background and related work

TODO: related work on endpoint reliability, proxy misconfiguration, IT automation evaluation.
Do not invent citations.

## 3. Problem formulation

- Primary RQ and secondary RQs — see `docs/research_question.md`.
- Failure taxonomy — see `docs/failure_taxonomy.md`.

## 4. System overview

- Evidence → classification → policy → preview → verification → audit.
- Proposed system = repository baseline **B3** (not ML).

## 5. Dataset

- Synthetic / fixture-derived dataset v1.
- Schema, splits, leakage controls — see `docs/dataset.md`.
- Table 1 (composition) — generate from experiment outputs; do not hardcode invented counts beyond committed `cases.jsonl`.

## 6. Baselines and proposed method

- B0, B1, B2, B_ML, B3 mapping — see `docs/methodology.md`.

## 7. Experimental setup

- Seeds, manifests, CI smoke vs full run.
- Metrics: accuracy, macro F1, FPR/FNR, safety posture match, runtime.
- Explicit non-claims: live MTTR, enterprise field rates.

## 8. Results

Results will be inserted automatically from the reproducible experiment pipeline.

Suggested tables (generated, not hand-edited):

- Table 2 — Main baseline comparison (`benchmarks/results.csv`)
- Table 3 — Per-class metrics
- Table 4 — Ablations (`benchmarks/ablations.csv`)
- Table 5 — Bootstrap CIs (`benchmarks/bootstrap_ci.csv`)

## 9. Ablation study

- A1–A7 component removals via `AblationConfig`.

## 10. Discussion

- Where B3 wins/loses; small-n uncertainty; construct limits of posture match.

## 11. Threats to validity

- See `docs/threats_to_validity.md`.

## 12. Conclusion

TODO after frozen results.

## Reproducibility appendix

```text
make research
# artifacts: benchmarks/*.csv, experiments/results/latest/metadata.json
```
