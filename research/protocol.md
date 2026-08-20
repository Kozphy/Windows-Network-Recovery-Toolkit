# Proxy Drift Benchmark Protocol v1

## Objective

Measure whether the context-aware proxy-drift classifier provides a meaningful improvement over simpler baselines, and identify which evidence dimensions are responsible for any improvement.

## Experimental units

One unit is a labeled endpoint scenario or replay trace with a known ground-truth state. Each scenario must include a stable identifier, scenario family, evidence payload, expected label, source type, and provenance metadata.

## Evidence source classes

1. **Synthetic** — generated combinations used to exercise known state boundaries.
2. **Controlled** — scenarios produced in a reproducible Windows test environment.
3. **Real-world evidence** — sanitized observed cases with provenance and explicit limitations.

Results must be reported separately by source class before any pooled summary.

## Baselines

### B0 — Naive proxy-enabled baseline
Predict drift whenever a proxy is enabled and a configured endpoint is unavailable. This intentionally weak baseline checks whether the research setup can distinguish trivial logic from richer classifiers.

### B1 — Static cross-source rule baseline
Use a fixed rule over current WinINET/WinHTTP state, without temporal history. Exact rules must be frozen before evaluation.

### P1 — Context-aware toolkit classifier
Use the current deterministic classifier with temporal/cross-source evidence enabled where available.

## Dataset split

- Development scenarios may be used to refine labels and implementation.
- Evaluation scenarios must be frozen before final metric calculation.
- Scenario-family leakage between development and evaluation sets must be documented.
- If multiple observations come from the same incident, group them to prevent train/test-style leakage.

## Metrics

For binary drift-vs-no-drift evaluation:

- TP, FP, TN, FN
- Precision = TP / (TP + FP)
- Recall = TP / (TP + FN)
- F1 = harmonic mean of precision and recall
- FPR = FP / (FP + TN)
- FNR = FN / (FN + TP)

For traces containing a known event start time:

- MTTD = mean(detection_time - event_start_time)

Report denominators together with rates. A metric with an undefined denominator must be reported as `NA`, not silently converted to zero.

## Uncertainty

Use stratified bootstrap resampling by scenario family for 95% confidence intervals when sample size permits. Report absolute and relative deltas versus B1. Do not rely on p-values alone.

## Ablations

Run P1 with one evidence family removed at a time:

- A1: no temporal state
- A2: no WinINET evidence
- A3: no WinHTTP evidence
- A4: no DNS context
- A5: no TLS/path context

If the current classifier cannot disable a component cleanly, record the ablation as blocked rather than approximating it invisibly.

## Error analysis

Every FP and FN must be assigned one primary failure category, for example:

- stale-but-benign configuration
- transient listener outage
- intentional policy transition
- conflicting WinINET/WinHTTP state
- missing temporal context
- ambiguous ground truth
- unsupported scenario

Retain a free-text note for cases that do not fit the taxonomy.

## Reproducibility requirements

Every benchmark run records:

- git commit SHA
- Python version
- operating system / Windows version when relevant
- dataset manifest hash
- random seed
- baseline version
- classifier version or commit
- command line
- timestamp

Raw observations and derived metrics must remain separable so results can be regenerated.

## Decision rule

H1 is supported only if P1 reduces FPR by at least 20% relative to B1 and recall declines by no more than 5 percentage points on the frozen evaluation set. Confidence intervals and failure categories must still be reported; meeting the threshold is not sufficient to claim enterprise-wide superiority.

## Threats to validity to track

- synthetic/controlled scenario realism
- label quality and ground-truth ambiguity
- repeated observations from the same incident
- Windows-version and enterprise-policy coverage
- unequal scenario-family prevalence
- implementation differences between baseline and proposed method
- benchmark overfitting
