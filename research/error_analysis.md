# Error Analysis

Every evaluation error should be reviewed at the case level.

## Taxonomy

- **E1 evidence missing** — required source absent or unreadable
- **E2 evidence conflict** — sources disagree and reconciliation is insufficient
- **E3 rule boundary** — case lies near a deterministic rule threshold
- **E4 label ambiguity** — ground-truth label is not uniquely defensible
- **E5 unsupported inference** — classifier conclusion exceeds available evidence
- **E6 stale-state artifact** — fixture contains temporally inconsistent state
- **E7 environment dependency** — result depends on OS/runtime behavior not represented in fixtures
- **E8 implementation defect** — code behavior contradicts the declared rule

## Required review record

For each false positive, false negative, and low-proof-tier case record:

1. case ID
2. expected label
3. predicted label
4. proof tier
5. decisive evidence
6. error category
7. whether the issue changes the hypothesis interpretation
8. remediation: code fix, fixture fix, label review, or documented limitation

Do not silently remove hard cases from the evaluation set. Any exclusion must be versioned and justified before rerunning final metrics.
