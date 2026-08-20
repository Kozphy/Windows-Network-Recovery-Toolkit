# Results Template

> Populate this file only from reproducible benchmark output. Do not hand-enter favorable numbers without retaining the raw predictions used to derive them.

## Main comparison

| Detector | Precision | Recall | Macro-F1 | False remediation rate | 95% CI |
|---|---:|---:|---:|---:|---:|
| B0 Registry-only | TBD | TBD | TBD | TBD | TBD |
| B1 WinINET-only | TBD | TBD | TBD | TBD | TBD |
| B2 WinHTTP + registry | TBD | TBD | TBD | TBD | TBD |
| B3 Full evidence fusion | TBD | TBD | TBD | TBD | TBD |

## Ablation study

| Configuration | Macro-F1 | Δ vs B3 | False remediation rate | Interpretation |
|---|---:|---:|---:|---|
| B3 Full | TBD | — | TBD | TBD |
| B3 - temporal | TBD | TBD | TBD | TBD |
| B3 - TLS | TBD | TBD | TBD | TBD |
| B3 - WinHTTP | TBD | TBD | TBD | TBD |
| B3 - connectivity | TBD | TBD | TBD | TBD |
| B3 - cross-source consistency | TBD | TBD | TBD | TBD |

## Error analysis

For each material error, retain `case_id` and classify the failure rather than deleting inconvenient cases.

| case_id | truth | prediction | FP/FN | failure category | explanation |
|---|---|---|---|---|---|
| TBD | TBD | TBD | TBD | TBD | TBD |

Suggested failure categories:

- insufficient evidence
- contradictory evidence
- transient/persistent ambiguity
- incorrect or uncertain ground truth
- Windows API inconsistency
- threshold/policy error
- fixture/measurement defect
- unknown

## Statistical reporting

For aggregate metrics, report the point estimate and bootstrap 95% confidence interval. Where two systems are compared on the same cases, prefer a paired resampling design. Report the size and direction of the observed effect; do not equate statistical significance with operational importance.

## Threats to validity

### Internal validity
Potential fixture errors, implementation coupling between baseline and proposed detector, threshold tuning on evaluation cases, and nondeterministic environmental behavior.

### Construct validity
Proxy drift labels and remediation safety metrics are operational proxies; they do not establish malware, compromise, or general endpoint health.

### External validity
A Windows-focused benchmark may not generalize across Windows versions, enterprise policies, VPN products, proxy software, networks, or organizations.

### Reproducibility
Record benchmark version, commit SHA, runtime, environment, command, seeds, raw predictions, and generated metrics for every reported table.

## Discussion prompts

1. Did B3 outperform the baselines consistently, or only on particular scenario families?
2. Which evidence source changed decisions most often?
3. Did higher classification performance also improve remediation safety?
4. Where did abstention outperform forced classification?
5. Which results contradicted H1–H3?
6. What new experiment would most strongly challenge the current conclusion?
