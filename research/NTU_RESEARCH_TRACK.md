# NTU Research Track: From Engineering Artifact to Research Artifact

This track is designed to make the repository easier to evaluate as a research portfolio. It does **not** claim affiliation with, acceptance by, or equivalence to National Taiwan University.

## Research thesis

**Working title:** Evidence Sufficiency for Safe Endpoint Remediation under Configuration Drift

The central question is no longer merely whether a Windows proxy fault can be detected. The research problem is:

> When is heterogeneous endpoint evidence sufficient to justify a remediation decision, and when should a system abstain and request human review?

This reframes the project from a repair toolkit into an empirical study of evidence, uncertainty, decision cost, and safe automation.

## Formal decision framing

Let `E = {e_registry, e_wininet, e_winhttp, e_dns, e_tls, e_connectivity, e_temporal}` be observed evidence. A policy chooses an action `a` from:

- `NO_ACTION`
- `REQUEST_MORE_EVIDENCE`
- `HUMAN_REVIEW`
- `REMEDIATION_PREVIEW`

The objective is not maximum classification accuracy alone. Evaluation should account for asymmetric decision costs:

`Risk(a) = C_FP * P(false remediation) + C_FN * P(missed persistent fault) + C_A * P(abstention)`

The cost values must be declared before evaluation or explored transparently in sensitivity analysis; they must not be selected after seeing test results to make the proposed method look favorable.

## Research questions

### RQ1 — Evidence sufficiency
When does multi-source evidence provide enough information to distinguish persistent configuration drift from transient failure?

### RQ2 — Safe abstention
Can an explicit abstention policy reduce false remediation decisions without making the system operationally useless?

### RQ3 — Temporal evidence
How much does temporal persistence contribute beyond a single endpoint snapshot?

### RQ4 — Distribution shift
How robust are decision rules when scenario frequencies, Windows configurations, or evidence availability differ from benchmark-development conditions?

## Hypotheses

- **H1:** Multi-source evidence fusion reduces false-remediation rate relative to single-source baselines.
- **H2:** Adding abstention reduces false-remediation rate at the cost of increased human-review rate.
- **H3:** Temporal evidence improves discrimination between transient and persistent failures.
- **H4:** Performance degrades under distribution shift; explicit uncertainty/abstention degrades more safely than forced classification.

These are hypotheses, not claims. Negative results must be retained.

## Experimental ladder

### E0 — Sanity checks
Verify benchmark labels, deterministic replay, metric implementation, and deliberately trivial cases.

### E1 — Baseline comparison
Compare B0 Registry-only, B1 WinINET-only, B2 WinHTTP+registry, and B3 full evidence fusion on a frozen test set.

### E2 — Ablation
Remove temporal, TLS, WinHTTP, connectivity, and cross-source-consistency evidence one family at a time.

### E3 — Abstention frontier
Sweep the evidence-sufficiency threshold and report the trade-off between false remediation and human-review/abstention rate. Do not select a threshold from the final test set.

### E4 — Distribution shift
Construct held-out scenario mixtures and missing-evidence conditions not used for rule/threshold development. Measure degradation and failure modes.

### E5 — Reproduction / external baseline
Select a relevant peer-reviewed systems, reliability, security-measurement, anomaly-detection, or safe-decision paper. Reproduce one central result before adapting the idea to this domain. Record deviations from the original experimental conditions.

## Required statistical discipline

For each primary metric:

1. Report sample count and class distribution.
2. Report point estimate and bootstrap 95% confidence interval.
3. Use paired resampling when comparing methods on identical cases.
4. Report absolute effect size, not only percentage improvement.
5. Keep development and final test data separate.
6. Freeze hypotheses and primary metrics before the final evaluation run.
7. Publish raw predictions sufficient to regenerate every table.

## Dataset split

Use three logically distinct sets:

- `development`: rule design and debugging
- `validation`: threshold selection and model/policy selection
- `test`: one-way final evaluation; do not tune on this set

For small datasets, scenario-grouped or provenance-grouped splitting is preferable to random row splitting when near-duplicate cases could leak across sets.

## Distribution-shift matrix

Evaluate at least these shifts:

| Shift | Question |
|---|---|
| Higher transient-failure prevalence | Does the system over-remediate? |
| Missing TLS evidence | Can it abstain safely? |
| Missing WinHTTP evidence | Is cross-source reasoning brittle? |
| Previously unseen proxy-state combination | Does forced classification become unsafe? |
| Noisy temporal observations | How sensitive is persistence reasoning? |

## Error-analysis protocol

Every false positive, false negative, and false remediation should receive a failure label. After labeling, summarize counts by failure category and select representative cases without hiding unfavorable examples.

For each representative failure answer:

1. What evidence was available?
2. What evidence was missing or contradictory?
3. Why did the decision rule fail?
4. Would abstention have been safer?
5. Is the failure an implementation bug, benchmark defect, or method limitation?
6. What experiment could falsify the proposed explanation?

## Paper-reproduction gate

Before describing the repository as a research-grade portfolio, complete at least one reproduction artifact:

```text
research/reproduction/<paper-key>/
  README.md
  environment.md
  reproduce.py
  original_claim.md
  reproduced_results.csv
  deviations.md
  critique.md
```

`critique.md` should cover the paper's problem, assumptions, strongest evidence, weaknesses, reproducibility gaps, and one extension hypothesis.

## Paper-shaped final artifact

Target a concise technical report:

1. Abstract
2. Introduction and research questions
3. Related work
4. Problem formulation
5. Evidence and decision model
6. Benchmark methodology
7. Baselines
8. Main results
9. Ablations
10. Abstention/safety trade-off
11. Distribution-shift evaluation
12. Error analysis
13. Threats to validity
14. Related limitations and negative results
15. Reproducibility statement
16. Conclusion

## Evidence required before stronger claims

Do not claim that the proposed system is "better," "safer," "research-grade," or "NTU-level" merely because this structure exists. Stronger language requires frozen data, reproducible experiments, external comparison, statistical reporting, and critical discussion.

## Definition of done

This track is complete when a reviewer can, from a clean environment:

1. identify the research question and preregistered hypotheses;
2. inspect provenance and train/development/test separation;
3. reproduce baseline and proposed-method predictions;
4. regenerate every result table;
5. inspect ablation and distribution-shift results;
6. inspect all material errors and negative results;
7. reproduce at least one external paper result or clearly document why reproduction failed;
8. read a concise paper that distinguishes evidence from interpretation.
