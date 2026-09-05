# Research Gap Analysis

> Repository: `Kozphy/Windows-Network-Recovery-Toolkit`
> Last updated: empirical evaluation upgrade pass (Phases 0–14 consolidation)

This document maps **existing capability** → **evidence currently available** → **missing empirical evidence** → **proposed experiment** → **required implementation** → **risk**.

See also: [`gap_analysis.md`](gap_analysis.md) (detailed tables).

---

## Summary matrix

| Area | Existing capability | Evidence currently available | Missing empirical evidence | Proposed experiment | Required implementation | Risk of implementation |
|------|---------------------|------------------------------|----------------------------|---------------------|-------------------------|------------------------|
| **Architecture** | Evidence tiers, policy gates, audit chain, dual CLI | Unit/contract tests; B3 uses classifier path | Live audit in benchmark loop | Extend run records only | `ExperimentRunRecord` fields | Low |
| **Baselines B0–B3** | All four in `experiments/baselines/` | `benchmarks/results.csv`, confusion matrices | Held-out-only headline table | Split-aware CSV export | Runner filter by split | Low |
| **Dataset v1** | 22 fixture cases in `benchmarks/dataset_v1/` | `cases.jsonl`, provenance | Reviewer-facing `datasets/v1/` mirror | Export scenarios view | `scenarios_export.sync_datasets_v1()` | Low |
| **Metrics** | Accuracy, macro/micro F1, FPR/FNR, unsupported rate | `experiments/metrics.py` | Wall-clock detection/recovery latency | Honest N/A latency CSV | `latency.csv` placeholder | Low (no fabrication) |
| **Statistics** | Bootstrap 95% CI, 1000 iterations | `benchmarks/bootstrap_ci.csv` | Formal significance tests | Keep bootstrap-only unless assumptions documented | `stats.py` | Low |
| **Ablations A1–A7** | Component removal deltas | `benchmarks/ablations.csv` | A3 naming vs “control testing” | Document mapping in report | TECHNICAL_REPORT section | Low |
| **Failure analysis** | B3 error taxonomy CSV | `benchmarks/error_analysis.csv` | Auto-generated narrative doc | Regenerate FAILURE_ANALYSIS.md | `research_docs.py` | Low |
| **Claims traceability** | Partial README claims | metrics + ablations | Matrix linking every claim | CLAIMS_EVIDENCE_MATRIX.md | `research_docs.py` | Low |
| **Reproducibility** | `make research`, run_all | metadata.json with git SHA | Single entry script for reviewers | REPRODUCING.md + reproduce.ps1 | Done this pass | Low |
| **CI gate** | Smoke benchmark + interaction tests | `.github/workflows/ci.yml` | Manifest schema validation | pytest manifest test | `test_manifest.py` | Low |
| **Recovery / MTTR** | Preview-only remediation posture | Posture match in safety metrics | Live apply/verify timing | Defer to v2 field study | Not in scope | N/A |
| **Interaction effects** | Phase 1 factorial module | `research/interactions/` | Nonlinear/regime phases | Phase 2+ roadmap | Separate modules | Medium (scope) |

---

## Reviewer questions (10-point checklist)

| # | Question | Status |
|---|----------|--------|
| 1 | What research questions are tested? | Documented in `RESEARCH.md`; B0–B3 addresses RQ1 |
| 2 | What are the baselines? | B0–B3 in `experiments/baselines/` |
| 3 | What dataset/scenarios? | v1: 22 synthetic/replayed fixtures; `datasets/v1/scenarios.jsonl` |
| 4 | How are experiments executed? | `python -m experiments.run_benchmark --manifest experiments/manifests/v1.json` |
| 5 | What metrics? | `benchmarks/results.csv`, per-class, safety, evidence |
| 6 | What uncertainty? | `benchmarks/bootstrap_ci.csv` (95% CI, seed 42) |
| 7 | Component ablations? | `benchmarks/ablations.csv` A1–A7 |
| 8 | Failure modes? | `docs/research/FAILURE_ANALYSIS.md` from error_analysis.csv |
| 9 | Reproducible? | `REPRODUCING.md`, `./scripts/reproduce.ps1` |
| 10 | Claims supported? | `docs/research/CLAIMS_EVIDENCE_MATRIX.md` |

---

## Anti-goals (do not duplicate)

- Do not add strawman baselines or new detectors for benchmark convenience.
- Do not disable policy gates or dry-run defaults.
- Do not hand-edit metric CSVs or invent numbers in markdown.
- Do not claim v1.0 “empirically evaluated release” until full pipeline run is recorded on target environment.

---

## Remaining gaps after this pass

1. **Held-out split reporting** in published README table (development vs held_out).
2. **Live Windows timing** — requires instrumented soak on real host (explicit opt-in).
3. **Enterprise field validation** — out of scope for fixture v1.
4. **Phases 2–14 decision-intelligence** (nonlinear, regime, calibration, causal) — roadmap only.

**Next recommended step:** Run `./scripts/reproduce.ps1`, commit artifacts with git SHA, optionally tag `v0.9-benchmark-ready`.
