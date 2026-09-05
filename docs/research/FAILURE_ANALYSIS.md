# Failure Analysis — Benchmark B3

> Auto-generated from `benchmarks/error_analysis.csv`. Do not hand-edit counts.

**Total B3 misclassifications:** 8

## Summary by category

| Category | Count | Rate | Example scenario IDs |
|----------|------:|-----:|----------------------|
| insufficient evidence | 7 | 87.50% | RB-v1-012, RB-v1-013, RB-v1-014 |
| wrong fault family | 1 | 12.50% | RB-v1-017 |

## Mitigation notes

- **Insufficient evidence:** Add probes/listeners to sparse fixtures; do not lower abstention threshold without review.
- **Wrong fault family:** Review label ambiguity vs classifier rule boundaries.
- **Dataset limitation:** Expand v2 corpus; avoid rewriting labels to inflate metrics.

## Reproduce

```powershell
python -m experiments.run_all
```
