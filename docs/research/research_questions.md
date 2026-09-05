# Research Questions — Evidence-Based Endpoint Risk and Decision System

> **Status:** Framework defined. Full comparative results are produced only by the reproducible experiment pipeline; this document does **not** invent outcomes.
> **Related:** [`research_architecture.md`](research_architecture.md) · [`research_grade_gap_analysis.md`](research_grade_gap_analysis.md) · [`../../RESEARCH.md`](../../RESEARCH.md)
> **Purple Team RQs (control validation):** [`../../research/questions.md`](../../research/questions.md)

---

## Central principle

```text
CLAIM → EVIDENCE → EXPERIMENT → COMPARISON → UNCERTAINTY → LIMITATION → CONCLUSION
```

Observation ≠ proof · Correlation ≠ causation · Classification ≠ accusation · Policy allow ≠ safety guarantee.

---

## RQ1 — Diagnostic Effectiveness

**Question.** How accurately can multi-source evidence-based diagnosis identify Windows endpoint connectivity failures compared with conventional rule-based, machine-learning, and LLM-based approaches?

### Hypothesis

**H1.** Under a fixed synthetic/fixture benchmark with independent ground-truth labels, the proposed evidence-tiered system (repo baseline **B3**) achieves higher **macro F1** and lower **false-positive rate** on non-healthy classes than B0 (connectivity-only) and B1 (flat rules), without increasing unsafe remediation proposals.

*ML (`B_ML`, Bernoulli NB) is included in the harness; LLM (`B_LLM`) remains optional/future. Small-n ML scores are methodological, not enterprise field claims.*

### Independent variables

| Variable | Levels |
|----------|--------|
| Diagnostic method | B0, B1, B2, B3 (proposed), later B_ML, B_LLM |
| Evidence availability | Full fixture vs incomplete / contradictory subsets |
| Split | `development` vs `held_out` |

### Dependent variables

- Predicted failure / incident class
- Abstention / insufficient-data rate
- Proof tier (proposed system)
- Policy / remediation posture

### Evaluation metrics

- Accuracy, macro precision/recall/F1, weighted F1
- Per-class F1; confusion matrix
- False-positive rate; false-negative rate
- Unsupported-classification rate; abstention rate
- Bootstrap 95% CI on primary metrics (case resampling)

### Experiment design

1. Load deterministic benchmark (`benchmarks/dataset_v1`, seed recorded).
2. Run each baseline through the shared prediction interface.
3. Score against `expected_incident_class` (labels not derived from predictions).
4. Report development and held-out separately when sample size allows.
5. Export `benchmarks/results.csv`, per-class tables, confusion matrices.

### Expected failure modes

- Healthy endpoints with unusual-but-valid config mislabeled as drift
- Compound failures collapsed to a single class
- Incomplete evidence forced into overconfident labels (abstention preferred)
- Label schema mismatch between incident classes and taxonomy IDs

### Validity threats

- Construct: fixture labels may not equal real enterprise “root cause”
- Internal: proposed system authors also authored some fixtures (overfit risk)
- External: synthetic Windows network states ≠ fleet diversity
- Statistical: n≈22 is small; CIs will be wide — do not over-claim significance

---

## RQ2 — Component Contribution

**Question.** Which evidence sources and decision-system components contribute most to diagnostic accuracy and false-positive reduction?

### Hypothesis

**H2.** Removing proof tiers, cross-signal aggregation, or selected evidence families (listener/TLS) measurably degrades macro F1 and/or increases FPR relative to the full configuration (ablations A1–A7).

### Independent variables

| Variable | Levels |
|----------|--------|
| Ablation config | FULL; −proof tiers; −listener/process; −TLS path; −limitations; −policy gate; −hash chain; −cross-signal aggregation |
| Dataset | Same fixed benchmark / seed |

### Dependent variables

- Classification metrics (accuracy, macro F1, FPR)
- Evidence metrics (explicit evidence / limitations rates)
- Safety metrics (unsafe proposal rate, policy match)

### Evaluation metrics

- Δmacro-F1, ΔFPR vs FULL
- Ablation table (`benchmarks/ablations.csv`)
- Optional paired bootstrap ΔCI (when implemented)

### Experiment design

1. Evaluate FULL (B3).
2. Re-run with `AblationConfig` flags (dependency injection — not forked copies).
3. Hold dataset and seed constant.
4. Attribute changes to the removed component only within this fixture world.

### Expected failure modes

- Ablation that strips labels’ necessary signals looks artificially large
- Policy-gate ablation improves accuracy while worsening safety (report both)
- Hash-chain ablation may not affect classification metrics (document as governance-only)

### Validity threats

- Ablations measure contribution *on this benchmark*, not causal necessity in production
- Components are not orthogonal (removing aggregation also changes evidence use)
- Small n limits interaction interpretation

---

## RQ3 — Remediation Safety

**Question.** Can verification-aware remediation improve repair success while reducing unsafe, unnecessary, or incorrect interventions?

### Hypothesis

**H3.** Policy-gated, preview-default remediation yields a lower **unsafe-action proposal rate** and higher **policy/remediation posture match** than an ungated ablation, on the same labeled cases.

### Independent variables

| Variable | Levels |
|----------|--------|
| Policy / verification posture | Full gates; −policy gate; preview-only vs (future) verify-after-apply |
| Case expected remediation | `NONE`, `PREVIEW_ONLY`, confirmation-required, `BLOCK` |

### Dependent variables

- Proposed remediation posture
- Unsafe action proposed (boolean)
- Policy match vs expected
- Verification success (fixture / dry-run only in default research path)

### Evaluation metrics

- Unsafe remediation rate
- Unnecessary intervention rate (action proposed when expected `NONE`)
- Policy match / correctly preview-only rate
- Audit verification rate (when chain exercised)
- **Not** live MTTR unless an instrumented, consented field study is added later

### Experiment design

1. Use safety columns already produced by the benchmark harness.
2. Compare FULL vs `remove_policy_gate` ablation.
3. Keep `DRY_RUN=True` for all automated research runs — **no destructive endpoint mutation in CI**.
4. Record limitations when verification is simulated rather than live.

### Expected failure modes

- Conflating “preview emitted” with “repair succeeded”
- Treating dry-run verification injects as live recovery proof
- Under-powered repair-success claims on preview-only labels

### Validity threats

- Construct: fixture `expected_remediation_posture` is a governance label, not measured repair
- External: enterprise change-control differs from local typed confirmation
- Internal: safety metrics can look perfect if baselines never propose apply

---

## Cross-cutting evaluation units

Each benchmark case should provide:

1. Input evidence (fixture path or inline synthetic)
2. Independent ground-truth failure / incident class
3. Minimum acceptable proof tier
4. Expected policy and remediation postures
5. Explicit limitations
6. Stable `case_id` / `scenario_id`
7. Provenance category (`synthetic_fixture`, `derived_from_existing_fixture`, …)
8. Split membership (`development` / `held_out`)

Ground truth **must not** be computed from the detector under test.

---

## What is not claimed yet

- No claim of statistical superiority over ML or LLM methods until those baselines run.
- No claim of enterprise MTTR reduction.
- No claim that synthetic results equal production SOC/IT outcomes.
- Research evaluation framework and fixture results ≠ peer-reviewed publication readiness alone.
