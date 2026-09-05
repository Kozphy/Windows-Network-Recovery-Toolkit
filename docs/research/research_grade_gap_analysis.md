# Research-Grade Upgrade — Gap Analysis

> **Artifact role:** planning input for the Evidence-Based Endpoint Risk and Decision System upgrade.
> **Date:** 2026-09-04
> **Rule:** reuse existing production and experiment code; do not duplicate detectors; do not invent results.

This analysis maps **existing capability** → **research requirement** → **gap** → **proposed change**.
It supersedes informal notes for the *research-grade* track. The earlier engineering gap table remains at [`gap_analysis.md`](gap_analysis.md).

---

## Inventory (what already exists)

| Area | Location | Status |
|------|----------|--------|
| Evidence → classify → policy → preview → audit | `windows_network_toolkit/`, `src/platform_core/` | Production logic |
| Fixture benchmark dataset v1 (22 cases) | `benchmarks/dataset_v1/`, `datasets/v1/` | Synthetic / fixture-derived |
| Baselines B0–B3 (connectivity, flat rules, single-signal, full platform) | `experiments/baselines/` | Runnable offline |
| Metrics (accuracy, macro F1, FPR/FNR, evidence, safety) | `experiments/metrics.py` | Implemented |
| Bootstrap 95% CI | `experiments/stats.py` → `benchmarks/bootstrap_ci.csv` | Implemented |
| Ablations A1–A7 via `AblationConfig` | `experiments/ablations.py` | Config-driven (good) |
| Error analysis CSV | `experiments/error_analysis.py` | Implemented |
| Experiment runner + metadata | `experiments/run_all.py`, `experiments/runner.py` | Implemented |
| Repro docs / smoke CI | `REPRODUCING.md`, `make research`, CI `eval-benchmarks` | Implemented |
| Purple Team RQ set | `research/questions.md` | Control-validation RQs (different axis) |
| Operator failure taxonomy (F1–F9) | `docs/failure-taxonomy.md` | Process failures, not endpoint classes |
| Purple simulation taxonomy | `research/failure_taxonomy.md` | Sim/detect stages, not F_PROXY_* |
| Interaction effects module | `research/interactions/` | Phase-1 factorial |
| Threats to validity (purple) | `research/threats_to_validity.md` | Partial; needs construct expansion |

**Absent / incomplete relative to the research-grade brief**

| Requirement | Gap |
|-------------|-----|
| Formal RQ1–RQ3 (diagnostic effectiveness, component contribution, remediation safety) | Not yet as `docs/research/research_questions.md` |
| Machine-readable endpoint failure taxonomy (`F_PROXY_001` …) | Markdown only; no YAML/Python integrity tests |
| Public `research/dataset/` schema + generators | Dataset lives under `benchmarks/`; no generator package for scale-out |
| Classical ML baseline | No sklearn/pure-ML baseline; B3 today is the **proposed system** |
| Optional LLM baseline (offline stub) | Provider abstractions exist elsewhere; no research adapter |
| McNemar / paired bootstrap Δ / permutation | Bootstrap CI only |
| Preprint skeleton `paper/` | Missing |
| `Dockerfile.research` with Windows/Linux split documented | Missing |
| Explicit data-leakage controls doc | Partially implied; no dedicated doc |
| Unified `python -m research.run_all` façade | Entry is `experiments.run_all` |

---

## Capability → Requirement → Gap → Change

| # | Existing capability | Research requirement | Gap | Proposed change | Phase |
|---|---------------------|----------------------|-----|-----------------|-------|
| 1 | `RESEARCH.md` + purple RQs | Formal RQ1–RQ3 with IVs/DVs/metrics/validity | Different RQ axis; purple RQs remain valid for control validation | Add `docs/research/research_questions.md`; keep purple RQs linked | 1 |
| 2 | Engineering architecture docs | Research pipeline diagram (claim→evidence→experiment) | No single research-architecture map | Add `docs/research/research_architecture.md` | 1 |
| 3 | F1–F9 + purple failure labels | Endpoint failure taxonomy with stable IDs | No machine-readable class catalog | `configs/failure_taxonomy.yaml` + `research/taxonomy.py` + tests | 2 |
| 4 | `benchmarks/dataset_v1` | Public research-safe schema + generators | Schema is incident-label oriented; limited generator API | `research/dataset/` wrapping/exporting v1 + seedable generators | 3 |
| 5 | B0–B3 function API | `DiagnosticBaseline` protocol + proposed adapter | No shared Protocol class; naming clash if B3=ML | Keep B0–B3 IDs; add Protocol + `B_ML`/`B_LLM`; map proposed = existing B3 | 4–5, 7, 14 |
| 6 | Metrics + safety metrics | Remediation outcome metrics (repair/unsafe/verify) | Repair success is posture-match on fixtures, not live repair | Document fixture semantics; add fields without fabricating MTTR | 6 |
| 7 | Percentile bootstrap | Paired comparisons | No McNemar / ΔCI | Extend `experiments/stats.py` or `research/evaluation/` | 9 |
| 8 | AblationConfig injection | Same (already correct pattern) | Naming differs from brief | Document mapping FULL/−verification/−policy… | 8 |
| 9 | Error analysis CSV | Confusion / FP / abstention narratives | Auto markdown exists; keep non-exaggerated | Extend without inventing claims | 10 |
| 10 | `make research` | `research-fast` / paper-tables / container | Partial Makefile targets | Add targets + `Dockerfile.research` | 12–13 |
| 11 | Purple threats doc | Full construct/internal/external/stat/LLM threats | Incomplete for diagnostic paper | Expand `docs/research/threats_to_validity.md` | 1 / 13 |
| 12 | README research scan | Dedicated Research Evaluation section | Present but product-first | Extend README section; no fabricated scores | 12 |

---

## Baseline ID mapping (critical)

The brief’s B3 = classical ML. **This repository already ships B3 = full evidence-tiered platform.**

| Brief ID | Repo ID (preserve) | Role |
|----------|--------------------|------|
| B0 naive | `B0` | Connectivity / majority-style weak baseline |
| B1 minimal rules | `B1` | Flat rules |
| B2 heuristic tree | `B2` | Single-signal / conventional heuristic |
| B3 classical ML | **new** `B_ML` (alias `B4` in manifests) | Logistic regression (optional sklearn) |
| B4 LLM | **new** `B_LLM` (alias `B5`) | Offline stub / optional live |
| Proposed system | **existing** `B3` | Evidence-tiered platform adapter |

Do **not** renumber existing published CSVs. Document aliases in manifests.

---

## Claims currently supported vs not supported

| Claim | Supported? | Evidence |
|-------|------------|----------|
| Fixture-only offline benchmark is reproducible | **Yes** | `REPRODUCING.md`, smoke CI, digests |
| B0–B3 comparable under one harness | **Yes** | `experiments/runner.py` |
| Component contribution via ablation | **Partial** | A1–A7 on fixture set; not field causal proof |
| Live enterprise MTTR / recovery timing | **No** | Explicitly deferred |
| Classical ML / LLM comparison | **No** | Not implemented yet |
| Statistical significance vs baselines | **No** | Bootstrap CI only; no automatic significance claims |

---

## Implementation principles

1. Prefer adapters over rewrites.
2. Keep dry-run / policy gates / offline CI intact.
3. Ground truth remains independent of detector output (`expected_*` fields).
4. Never commit secrets, real PII, or invented metric tables.
5. Separate Windows evidence collection from Linux-evaluable benchmark paths.

---

## Next steps

1. **Phase 1** — research questions + architecture + threats outline (this pass).
2. **Phase 2** — machine-readable endpoint taxonomy + integrity tests.
3. Continue phases only while `tests/experiments` and `tests/research` stay green.
