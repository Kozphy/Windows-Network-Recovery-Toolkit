# Research Architecture

Maps the existing Technology Risk & Control Analytics Platform into a reproducible research artifact.

```text
Evidence Collection (Windows / fixtures)
        ↓
Structured Failure Taxonomy (F_* IDs)
        ↓
Ground-Truth Benchmark (synthetic / fixture-derived)
        ↓
Diagnostic Methods
 ┌────────┬──────────┬────────┬───────────┬─────────┐
 │ B0     │ B1/B2    │ B_ML   │ B_LLM*    │ B3      │
 │ naive  │ rules /  │ class. │ optional  │ proposed│
 │        │ heuristic│ ML     │ stub/API  │ system  │
 └────────┴──────────┴────────┴───────────┴─────────┘
        ↓
Common Evaluation Harness (`experiments/`)
        ↓
Statistical Evaluation (bootstrap CI; later paired tests)
        ↓
Ablation (`AblationConfig`)
        ↓
Failure Analysis
        ↓
Risk-Aware Remediation (preview / policy — dry-run default)
        ↓
Verification + Audit (hash chain)
        ↓
Reproducible Research Artifact → Preprint skeleton
```

\*LLM baseline must remain optional and offline-capable (stub/cache).

---

## Module ownership (reuse, do not fork)

| Concern | Canonical location | Research role |
|---------|-------------------|---------------|
| Collectors / classify / policy / remediation | `windows_network_toolkit/`, `src/platform_core/` | Proposed system implementation |
| Fixture cases + labels | `benchmarks/dataset_v1/` | Ground truth v1 |
| Baseline predictions | `experiments/baselines/` | B0–B3 today; extend with B_ML / B_LLM |
| Metrics / CI / ablations / error analysis | `experiments/*.py` | Evaluation harness |
| Purple control validation | `src/purple_team/`, `research/questions.md` | Orthogonal RQ set |
| Endpoint failure taxonomy (machine-readable) | `configs/failure_taxonomy.yaml`, `research/taxonomy.py` | Class catalog |
| Public dataset façade / generators | `research/dataset/` (Phase 3) | Scale-out + schema docs |
| Preprint | `paper/` (later phase) | Structural only until results exist |

---

## Shared interfaces (target)

```text
EvidenceRecord  →  DiagnosticBaseline.predict(...)  →  DiagnosticDecision
```

Existing code uses `BenchmarkCaseV1` + `BaselinePrediction`. Adapters should wrap these types rather than replace them, preserving CSV schemas and CLI output.

**Proposed system** = existing `predict_b3` / full platform path, optionally wrapped as `ProposedEvidenceDecisionSystem`.

---

## Separation: Windows runtime vs offline evaluation

| Layer | Runs on | Notes |
|-------|---------|-------|
| A. Evidence collection / live WinINET-WinHTTP | Windows host | Not fully reproducible in Linux CI containers |
| B. Fixture load → baselines → metrics → plots | Any OS with Python 3.11+ | Default research path; CI smoke |

Document container limits in `Dockerfile.research` when added. Never claim a Linux container reproduces registry/network mutation behavior.

---

## Safety boundary (research runs)

- Default: fixture-only, `DRY_RUN` / preview posture.
- No process kill, firewall reset, or adapter disable in benchmarks.
- No API keys in repo; LLM path must degrade to stub.
- Audit and policy soft-fail/fail-closed rules from product code remain in force.

---

## Entry points

| Goal | Command |
|------|---------|
| Full offline research | `make research` → `python -m experiments.run_all` |
| Fast smoke | `make research-smoke` |
| Interactions | `make research-interactions` |
| Future façade | `python -m research.run_all` (thin wrapper; Phase 12) |

---

## References

- Research questions: [`research_questions.md`](research_questions.md)
- Gap analysis: [`research_grade_gap_analysis.md`](research_grade_gap_analysis.md)
- Reproduce: [`../../REPRODUCING.md`](../../REPRODUCING.md)
- Experiment contract: [`../../experiments/README.md`](../../experiments/README.md)
