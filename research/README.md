# Empirical Research Evaluation

This directory turns the platform's engineering claims into falsifiable, reproducible research questions. It intentionally separates **implemented evaluation infrastructure** from **results not yet measured**. No performance number should be reported until generated from a versioned benchmark run.

## Research questions

### RQ1 — Evidence fusion
How accurately can multi-source Windows network evidence distinguish persistent proxy-configuration drift from transient network failures?

**H1.** A detector combining WinINET, WinHTTP, registry, connectivity, and temporal evidence will reduce false remediation recommendations relative to single-source baselines on the repository benchmark.

### RQ2 — Evidence contribution
Which evidence sources contribute most to correct classification and safe remediation decisions?

**H2.** Removing temporal or cross-source consistency evidence will degrade classification performance more than removing low-discrimination evidence sources.

### RQ3 — Safety
Does evidence fusion reduce unsafe remediation recommendations when evidence is incomplete or contradictory?

**H3.** The full policy-gated system will have a lower false-remediation rate than baseline detectors.

## Evaluation protocol

1. Freeze a versioned benchmark manifest with scenario IDs and ground truth.
2. Run every baseline and the proposed system on the exact same cases.
3. Record predictions and remediation decisions without manual correction.
4. Compute precision, recall, F1, confusion matrices, false-remediation rate, and bootstrap confidence intervals.
5. Run ablations by removing one evidence family at a time.
6. Inspect false positives and false negatives and assign a failure-taxonomy label.
7. Report limitations and threats to validity before making general claims.

## Baselines

| ID | Detector | Purpose |
|---|---|---|
| B0 | Registry-only | Minimal static configuration baseline |
| B1 | WinINET-only | User proxy-state baseline |
| B2 | WinHTTP + registry rules | Cross-source deterministic baseline |
| B3 | Full evidence-fusion system | Proposed system |

B0–B2 are evaluation baselines, not production recommendations.

## Primary metrics

- Precision, recall, F1 by incident class
- Macro-F1 across classes
- False remediation rate: incorrect APPLY/repair recommendation divided by all repair recommendations
- Abstention / NOT_TESTED rate where evidence is insufficient
- Bootstrap 95% confidence intervals for aggregate metrics

Accuracy alone is not sufficient because scenario classes may be imbalanced and an unsafe false remediation has different operational consequences from abstention.

## Ablation plan

Starting from B3, evaluate:

- `B3 - temporal`
- `B3 - TLS`
- `B3 - WinHTTP`
- `B3 - connectivity`
- `B3 - cross_source_consistency`

An ablation is meaningful only if all other inputs, cases, thresholds, and random seeds are held constant.

## Benchmark schema

Each benchmark row should contain at least:

```text
case_id
scenario_family
ground_truth
registry_state
wininet_state
winhttp_state
dns_result
tls_result
connectivity_result
temporal_state
expected_action
source_provenance
```

Do not place sensitive endpoint data in the public benchmark. Prefer synthetic or deliberately captured, redacted fixtures with provenance.

## Reproducibility contract

Every published result must record:

- git commit SHA
- benchmark version
- Python/runtime version
- OS/environment where relevant
- detector/baseline ID
- random seed when applicable
- exact command used
- raw prediction artifact
- generated metric artifact

## Results status

**No empirical superiority claim is made by this document.** Tables remain unfilled until the benchmark runner produces results. A future paper/report should distinguish observations from interpretation and should include negative results.

## Planned paper structure

1. Abstract
2. Introduction
3. Problem definition
4. Related work
5. System and evidence model
6. Benchmark and experimental setup
7. Results
8. Ablation study
9. Error analysis
10. Threats to validity
11. Discussion
12. Reproducibility
13. Conclusion
