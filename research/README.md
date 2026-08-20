# Research & Audit-Grade Evaluation

This directory turns the platform from a portfolio implementation into a falsifiable, reproducible evaluation framework.

## Research question

Can multi-source Windows proxy-state reconciliation detect configuration drift more reliably than a single-source inspection strategy while preserving explainability, deterministic replay, and safety boundaries?

## Evaluation chain

`claim -> hypothesis -> dataset -> baseline -> experiment -> metrics -> ablation -> error analysis -> reproducibility -> limitations -> discussion`

## Files

- `hypotheses.md` — falsifiable hypotheses and rejection criteria
- `experimental_protocol.md` — fixed evaluation protocol
- `dataset_card.md` — provenance, scope, leakage and representativeness limits
- `baselines.md` — comparison systems
- `metrics.md` — primary/secondary metrics and uncertainty reporting
- `ablation_plan.md` — component-removal tests
- `error_analysis.md` — taxonomy and review procedure
- `reproducibility.md` — deterministic execution contract
- `limitations.md` — non-claims and external-validity limits
- `research_discussion.md` — how to interpret positive, null, or negative results

## Principle

Passing unit tests is necessary but not sufficient. A research claim is supported only when a frozen protocol produces repeatable results against explicit baselines and reports failures as carefully as successes.
