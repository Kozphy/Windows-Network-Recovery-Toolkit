# Metrics

## Primary

- **Macro-F1** across pre-declared incident classes

Macro-F1 is primary because rare but important failure classes should not be hidden by dominant healthy cases.

## Secondary

- per-class precision, recall, F1
- false-positive rate for drift alerts
- false-negative rate for declared critical drift classes
- balanced accuracy
- explainability completeness rate
- deterministic replay rate
- proportion of cases by proof tier T0–T5

## Safety metrics

- autonomous-remediation authorization count: target 0
- malware/compromise verdict count from reliability evidence: target 0
- classifications missing `limitations[]`: target 0

## Uncertainty

For classification metrics, report 95% bootstrap confidence intervals using 10,000 resamples and a recorded seed when sample size permits. For very small samples, emphasize raw counts and case-level outcomes rather than overstating interval precision.

## Reporting template

| System | Macro-F1 | 95% CI | FPR | Critical recall | Explainability completeness | Replay rate |
|---|---:|---:|---:|---:|---:|---:|
| B0 Always healthy | TBD | TBD | TBD | TBD | N/A | 100% |
| B1 WinINET only | TBD | TBD | TBD | TBD | TBD | 100% |
| B2 WinHTTP only | TBD | TBD | TBD | TBD | TBD | 100% |
| B3 mismatch heuristic | TBD | TBD | TBD | TBD | TBD | 100% |
| B4 full classifier | TBD | TBD | TBD | TBD | TBD | 100% |

Do not replace TBD values with estimates or hand-picked examples. They must come from the frozen evaluation run.
