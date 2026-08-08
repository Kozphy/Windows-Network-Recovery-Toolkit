# Research Validation Layer

This directory turns the existing production-shaped Windows endpoint reliability platform into a reproducible research artifact without changing the project's safety posture.

## Research theme

**Evidence-Guided Decision Systems for Safe Endpoint Reliability Automation**

The core question is not whether the toolkit can diagnose incidents, but whether its deterministic multi-source evidence model improves decision quality over simpler baselines while preserving explicit safety boundaries.

## Research questions

1. Does multi-source evidence fusion reduce false-positive remediation recommendations compared with simple heuristic rules?
2. How much do proof tiers (T0-T5) improve classification precision, recall, and abstention quality?
3. Which evidence sources contribute most to correct incident classification?
4. How robust is the classifier under missing, stale, contradictory, or duplicated evidence?
5. What trade-off exists between diagnostic latency and decision quality?

## Evaluation dimensions

- classification accuracy
- precision / recall / macro F1
- false-positive remediation rate
- abstention / NOT_TESTED rate
- decision latency
- reproducibility across fixed seeds and fixture revisions
- robustness under missing or corrupted evidence

## Structure

- `methodology.md` — hypotheses, experimental design, metrics, and validity controls
- `baselines.md` — comparison systems that are intentionally simpler than the platform
- `ablation_plan.md` — source-removal and capability-removal experiments
- `reproducibility.md` — deterministic execution and reporting requirements
- `limitations.md` — claims the research must not make

## Safety boundary

Research experiments must remain fixture-first and preview-only. They must not introduce autonomous remediation, malware attribution, EDR/XDR claims, or AI-authorized execution.
