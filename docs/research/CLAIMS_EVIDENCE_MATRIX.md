# Claims-to-Evidence Matrix

| Claim | Type | Metric | Dataset | Baseline | Artifact | Supported? |
|-------|------|--------|---------|----------|----------|------------|
| Hash-chained audit implemented | Engineering | audit_verification_rate | N/A | B3 | safety_metrics.csv | Yes (code + test) |
| B3 macro F1 exceeds B1 on dataset v1 | Research | macro_f1 | v1 fixtures | B3 vs B1 | metrics.csv @ e09566bb | Yes (0.5852 vs 0.4233) |
| Replay deterministic for B3 | Research | classification_agreement_rate | v1 | B3 | reproducibility_metrics.csv | Yes (1.0 on fixtures) |
| Policy gate blocks unsafe proposals (A5) | Safety | unsafe_action_proposal_rate | v1 | B3 | ablations.csv | Supported in ablation |
| Reduces enterprise MTTR | Product aspiration | — | — | — | — | **Not tested** |
| Prevents all unsafe remediation | Safety (strong) | unsafe_action_proposal_rate=0 | v1 | B3 | safety_metrics.csv | Scoped to fixtures only |

## Discipline

- **Engineering claim:** verifiable from code/tests.
- **Research claim:** requires benchmark artifact + dataset version + git SHA.
- **Safety claim:** must scope to synthetic fixtures unless live trials exist.
