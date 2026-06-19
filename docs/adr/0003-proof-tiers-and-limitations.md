# ADR-0003: Proof Tiers and Limitations

## Status

Accepted

## Context

Audit and interview audiences collapse "we saw a process on the port" into "malware changed the registry." Without explicit tiers and mandatory limitations, dashboards and AI narratives over-claim causation and attribution.

## Decision

Adopt **T0–T5 evidence tiers** in `evidence_schema.EvidenceTier` aligned with [proxy-proof-ladder.md](../proxy-proof-ladder.md):

- Tiers label claim strength at normalization time
- `STANDARD_LIMITATIONS` appended to normalized events
- Transition events include transition-specific limitations
- Platform export uses related T0–T4 proof tier dimension with `maturity_order`
- Classifications include `unsafe_inferences_blocked` (e.g. malware accusation blocked without writer proof)

Tiers **never auto-upgrade** when data passes through scoring or BI export.

## Alternatives considered

| Alternative | Why rejected |
|-------------|--------------|
| Single boolean `proven` flag | Hides nuance; fails Big 4 evidence quality questions |
| Probability per tier | Implies calibrated Bayesian model we do not have |
| Omit limitations in JSON | Invites misleading executive summaries |

## Consequences

- Every user-facing output is longer — intentional
- PARTIAL control tests are normal without Sysmon
- Documentation must keep endpoint T4 (writer) vs platform T4 (operator confirmed) mapping explicit

## Security considerations

- Prevents accusatory labels from triggering unsafe automated response
- MITM and malware language gated by tier and classification rules

## Audit considerations

- Workpapers can cite tier per observation
- CTRL-006 enforces non-accusatory triage for unknown proxy
- Reviewers should verify limitations visible in Power BI tooltips

## What this prevents

- Dashboard readers inferring compromise from HIGH risk alone
- Skipping attribution rungs in investigation narrative
- AI-generated text upgrading "correlated" to "caused by"

## What this does not prove

- That tier assignment is always optimal for edge cases
- Writer identity at T4 (proves write event, not intent)
- Regulatory compliance with any specific framework clause

## Interview defense

"T2 is listener correlation. T4 is Sysmon E13. I won't say 'malware' at T2 — the code literally blocks that inference in `build_explainable_classification`."
