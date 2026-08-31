# Purple Team Gap Analysis

**Status:** Phase 0 assessment
**Date:** 2026-08-24
**Scope:** Upgrade path from Blue Team diagnostic/recovery toolkit → Purple Team security *control validation* platform.

## Positioning (non-claims)

This repository is **not** antivirus, EDR, XDR, malware attribution, or autonomous offensive tooling.
Purple Team work here means: **safe, deterministic, reversible, fixture-driven experiments that measure whether defensive *controls* (observation → detection → gated response → verification) actually work.**

## Before (Blue Team strengths)

| Capability | Location | Reuse |
| --- | --- | --- |
| Fixture-first proxy/incident classification | `windows_network_toolkit/incident_classifier.py`, `analytics_pipeline.py` | Detection baseline |
| Policy-gated remediation + dry-run | `proxy_remediation.py`, `safety.py`, confirmation tokens | Response / approval |
| Operator incident compose | `src/proxy_drift/operator_incident_card.py` | Classification UX |
| Hash-chained custody + tip | `src/platform_core/audit/` | Evidence integrity |
| Classifier / replay benchmarks | `src/platform_core/evaluation/` | Evaluation seed |
| Telemetry readers (fixture) | `telemetry/`, `evidence/` | Collector adapters |
| Epistemic limitations[] | throughout | Explainability |

## Gaps vs Purple Team lifecycle

| Stage | Status | Gap |
| --- | --- | --- |
| Scenario definition | Missing | Typed schema with safety + rollback required fields |
| Safety / authorization gate | Partial | Remediation gates exist; no scenario-execution gate |
| Controlled adversarial simulation | Partial | Fixtures/fleet sim; no purple scenario runner |
| Telemetry normalization | Partial | Multiple schemas; no purple common event model |
| Detection engine | Partial | Classifiers exist; no modular DET-* rule interface |
| Risk classification | Partial | Risk fields exist; no documented weighted purple score |
| Response recommendation vs execution | Strong | Keep separation |
| Post-remediation verification | Partial | Some verify helpers; not first-class post-conditions |
| Effectiveness measurement | Partial | Benchmarks exist; not purple TP/FP/F1/MTTD suite |
| Immutable evidence | Partial | Custody chain; no per-run purple evidence bundle |
| Orchestration | Missing | No end-to-end state machine |
| Research layer | Missing | RQ / hypotheses / ablation / threats to validity |
| Portfolio framing | Missing | README still primarily recovery-toolkit oriented |

## Technical debt / risks

1. Dual stacks (`platform_core/` vs `src/platform_core/`, top-level `proxy_*` vs `src/proxy_*`).
2. Custody is **tamper-evident**, not WORM / legally immutable — document trust assumptions.
3. Live Windows mutation must stay out of generic CI; purple scenarios in CI are fixture-only.
4. Product boundary: do not add credential theft, persistence, stealth, MITM, or exploit tooling.

## Recommended placement

`src/purple_team/` — thin orchestrator that **imports** existing classifiers, safety, and custody rather than forking them. Scenario YAML under `scenarios/`. Research under `research/`.

## Migration plan (phases)

0. Gap analysis (this doc)
1. Scenario schema + safety gate + state machine
2. Telemetry + detection rules + pos/neg tests
3. Recommendation / approval / verification / rollback
4. Benchmark + baselines + failure taxonomy
5. Research docs + ablation + error analysis
6. Evidence bundles + reports
7. CLI, CI smoke, README, upgrade report

## Acceptance bar

See purple-team upgrade acceptance criteria: five safe scenarios, dry-run deny-by-default, measurable FP/FN, independent verification, reproducible fixture benchmarks, architecture + threat + safety docs.
