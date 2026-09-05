# Benchmarks

## Research publication package

- English preprint: `paper/proxy-risk-benchmark-v1-preprint.md`
- External-user protocol: `validation/external-user-study-v1.md`
- De-identified response template: `validation/external-user-study-v1-template.csv`

The external protocol is published for execution; no external-validation result is claimed until independently collected records pass the protocol's claim gate.

This directory contains **generated, reviewable benchmark evidence**.

The quantitative outputs are produced by the experiment workflow in
[`../experiments/README.md`](../experiments/README.md). Versioned output belongs under
`benchmarks/v1/`; every aggregate must be reproducible from case-level JSON and a
digest-verified manifest.

## Planned artifacts

```text
benchmarks/
  README.md
  v1/
    results.csv
    per_class_metrics.csv
    confusion_matrix.csv
    ablations.csv
    failure_analysis.md
    environment.json
    benchmark_report.md
```

## Evidence contract

Every published benchmark artifact must be traceable to:

- a Git commit SHA,
- a versioned dataset or fixture manifest,
- an experiment configuration,
- a deterministic or explicitly seeded runner,
- raw case-level outputs,
- the script used to derive the aggregate metrics.

## `results.csv`

Recommended schema:

```text
benchmark_version
split
model_or_baseline
case_count
accuracy
macro_precision
macro_recall
macro_f1
unsupported_classification_rate
abstention_rate
unsafe_action_proposal_rate
replay_mismatch_count
git_commit
dataset_digest
```

## `confusion_matrix.csv`

Recommended long-form schema:

```text
benchmark_version
split
model_or_baseline
expected_class
predicted_class
count
```

This format is easier to analyze with Python, SQL, or Power BI than a manually formatted matrix.

## `ablations.csv`

Recommended schema:

```text
benchmark_version
split
ablation
case_count
macro_f1
unsupported_classification_rate
unsafe_action_proposal_rate
replay_mismatch_count
delta_macro_f1_vs_full
delta_unsupported_rate_vs_full
notes
```

## Reviewer rules

A reviewer should be able to answer all of the following:

1. What exact code produced this number?
2. Which cases were evaluated?
3. Was the case set used while designing the classifier?
4. What baseline was compared?
5. Can the metric be regenerated from raw outputs?
6. What failed?
7. What does the result **not** prove?

If any of those questions cannot be answered, the benchmark is not yet publication-ready.

## Claim examples

### Acceptable before measurement

> The repository now defines a reproducible protocol for comparing evidence-tiered diagnosis with simpler baselines.

### Acceptable after measurement

> On benchmark v1 held-out fixtures, the full platform achieved X macro F1 versus Y for the flat-rule baseline. See `results.csv`, commit `<sha>`, dataset digest `<digest>`.

### Not acceptable

> The platform is 30% better than traditional troubleshooting.

That statement is too broad unless the experiment operationalizes "better," defines "traditional troubleshooting," and reports a valid comparison.

## Why this exists

The platform already demonstrates substantial engineering breadth. This benchmark layer is meant to prevent a common portfolio failure mode: presenting architectural sophistication as if it were empirical evidence.

The strongest version of this repository should show both:

- **engineering maturity** — architecture, safety controls, testing, auditability, deployment shape; and
- **research discipline** — baselines, held-out evaluation, ablations, reproducibility, limitations, and traceable claims.
