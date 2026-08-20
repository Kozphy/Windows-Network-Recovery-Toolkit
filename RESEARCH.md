# Research Evaluation Framework

This repository is primarily an engineering and technology-risk platform. This document adds a research-style evaluation layer so that claims about the system can be tested rather than inferred from feature count.

## Implementation status — synthetic benchmark v1

The first minimal execution layer is now implemented under [`experiments/`](experiments/README.md):

- 12 frozen, synthetic cases split across development, held-out, and adversarial directories;
- executable B0 connectivity-only, B1 flat-rule, B2 single-signal, and B3 full-platform adapters;
- repeated deterministic replay with per-prediction digests;
- executable component ablations;
- machine-derived CSV/JSON metrics and a generated Markdown report;
- tests for dataset integrity, expected-label isolation, determinism, and safety boundaries.

This implementation does **not** prove the hypotheses below. The dataset is small,
repository-authored, and synthetic; the held-out directory is a workflow boundary rather than an
independent external validation set. Generated failures are research evidence and must not be
edited away.

## Research question

**Can deterministic, evidence-tiered endpoint diagnosis improve classification quality, auditability, and decision reproducibility compared with simpler rule-based troubleshooting baselines?**

The project does **not** claim that the answer is already proven. The purpose of this framework is to define how the question should be tested.

## Hypotheses

- **H1 — Classification quality:** evidence-tiered classification will reduce unsupported or ambiguous classifications compared with a flat rule baseline.
- **H2 — Reproducibility:** fixture replay will produce identical classifications, proof tiers, policy decisions, and content digests for identical evidence inputs.
- **H3 — Safety:** policy-gated remediation previews will reduce unauthorized or unsafe action proposals relative to an ungated remediation baseline.
- **H4 — Auditability:** hash-chained audit records will make post-hoc decision reconstruction and tamper detection measurably more reliable than plain unlinked logs.
- **H5 — Evidence contribution:** removing proof-tier or cross-signal evidence will degrade at least one target metric, demonstrating that the additional evidence layer contributes information rather than documentation overhead alone.

## Evaluation units

Use sanitized fixtures and replayable synthetic cases. Each case should contain:

1. input evidence,
2. expected incident class,
3. expected proof tier or minimum acceptable tier,
4. expected control outcomes,
5. expected policy posture,
6. explicit limitations,
7. expected remediation posture (for example PREVIEW_ONLY), and
8. a stable case identifier.

Real-world evidence may be used only when it is sanitized, lawful to publish, and accompanied by a provenance note.

## Baselines

At minimum, compare the platform against the following baselines:

### B0 — Connectivity-only baseline

Classify an endpoint as healthy/unhealthy using only a basic reachability result. This represents a weak operational baseline and should expose the failure mode where a host is online but browser/application paths fail.

### B1 — Flat rule baseline

Use the same observable signals but without proof tiers, evidence aggregation, or cross-signal reasoning. Rules directly map observations to labels.

### B2 — Single-signal diagnostic baseline

Use only one evidence family, such as WinINET proxy configuration, listener state, or TLS-path result.

### B3 — Full platform

Use deterministic evidence aggregation, proof tiers, control tests, policy gates, limitations, audit logging, and replay.

The goal is not to make the baselines intentionally bad. Each baseline must be implemented as a credible simplified alternative.

## Primary metrics

### Classification

Report:

- accuracy,
- macro precision,
- macro recall,
- macro F1,
- per-class precision/recall,
- confusion matrix,
- unsupported-classification rate,
- abstention / NOT_ENOUGH_EVIDENCE rate.

When class imbalance is material, macro metrics take priority over raw accuracy.

### Evidence quality

Report:

- proportion of classifications with explicit supporting evidence,
- proportion with explicit limitations,
- proof-tier distribution,
- contradiction rate between evidence sources,
- cases downgraded because proof is incomplete.

### Reproducibility

For repeated runs over identical fixtures, report:

- classification agreement,
- proof-tier agreement,
- policy-decision agreement,
- digest agreement,
- replay mismatch count.

Target for deterministic fixture replay: **100% agreement** unless randomness is intentionally introduced and seeded.

### Safety / governance

Report:

- unsafe-action proposal rate,
- actions correctly blocked by policy,
- actions correctly restricted to preview,
- false blocks of permitted actions,
- missing approval requirements,
- audit-chain verification success.

### Operational usefulness

Where a controlled study is possible, report:

- time-to-diagnosis,
- number of diagnostic steps,
- number of setting changes attempted,
- number of reversals / unnecessary remediations.

Do not claim MTTR improvement without a study that actually measures it.

## Ablation study

Run the full platform and then remove one component at a time:

| Ablation | Removed capability | Question |
|---|---|---|
| A1 | Proof tiers | Do evidence confidence levels improve supported classification? |
| A2 | Listener/process evidence | Does endpoint-path attribution degrade? |
| A3 | TLS-path evidence | Are path-specific failures misclassified more often? |
| A4 | `limitations[]` | Does apparent confidence increase while evidence quality decreases? |
| A5 | Policy gate | Does unsafe remediation proposal rate increase? |
| A6 | Hash-chain linking | Does tamper detection degrade? |
| A7 | Cross-signal aggregation | Does a flat rule system produce more false positives? |

Each ablation must use the same dataset and seeds as the full-system run.

## Experimental protocol

1. Freeze the code revision and record the Git commit SHA.
2. Freeze the fixture dataset and compute a manifest digest.
3. Define labels and expected outcomes before examining aggregate results.
4. Run all baselines and the full platform on the same cases.
5. Store raw machine-readable outputs under `experiments/results/`.
6. Compute metrics from raw outputs, never by manual transcription.
7. Run ablations using the same cases.
8. Record runtime environment and Python/package versions.
9. Publish failed cases and limitations, not only successful examples.
10. Re-run from a clean environment before publishing conclusions.

## Statistical discipline

For small fixture datasets, report exact counts alongside percentages. Do not imply population-level significance from a portfolio-scale sample. If confidence intervals or significance tests are reported, document the test, assumptions, and sample size.

## Threats to validity

### Internal validity

Fixtures may encode assumptions that favor the classifier. Mitigation: create cases from multiple sources and include adversarial or ambiguous cases.

### External validity

Windows proxy/TLS cases are not representative of all endpoint failures, platforms, or enterprise environments. Conclusions should remain scoped to the evaluated failure families.

### Construct validity

A correct label does not necessarily mean a useful operational decision. Classification metrics therefore should be paired with evidence-quality and safety metrics.

### Dataset leakage

If fixtures were created while implementing classifier rules, evaluation can overestimate generalization. Maintain a held-out fixture set that is not used during rule development.

### Human factors

Auditability and operator usefulness may require human evaluation. Automated metrics alone cannot establish that a report is understandable to auditors, SREs, or support engineers.

## Reproducibility contract

A publishable experiment should provide:

```text
experiments/
  README.md
  manifest.json
  baselines/
  configs/
  results/
  scripts/
benchmarks/
  README.md
  results.csv
  confusion_matrix.csv
  ablations.csv
```

A reviewer should be able to reproduce reported tables from raw fixtures without editing source code.

## Claim policy

Until measurements exist, use language such as:

- "designed to improve reproducibility",
- "evaluates whether evidence tiers reduce unsupported classifications",
- "provides a protocol for comparing against simpler baselines".

After measurements exist, claims must point to a benchmark artifact and code revision.

Avoid unsupported statements such as:

- "reduces MTTR by 30%",
- "improves precision by 18%",
- "enterprise-grade accuracy",
- "proven safer than existing tools".

## Publication-ready endpoint

The research layer is considered mature when the repository contains:

1. a versioned benchmark dataset,
2. credible baselines,
3. machine-generated metrics,
4. an ablation study,
5. documented threats to validity,
6. a one-command reproduction path, and
7. a short technical report whose claims are traceable to benchmark outputs.

This creates a clear separation between **engineering capability**, **portfolio demonstration**, and **empirically supported research claims**.
