# ADR-0009: Confidence Is Ordinal, Not Probability

## Status

Accepted

## Context

Stakeholders interpret `confidence: 0.92` as "92% chance of compromise" or "92% probability the fix works." That misreads heuristic scores as calibrated Bayesian probabilities — unsafe for audit and engineering decisions.

## Decision

All confidence fields use **ordinal semantics**:

- `proxy_state_machine`: `confidence_semantics: ordinal_not_probability`
- `risk_scoring_engine`: explicit limitations — not statistical probability
- `IncidentRecord.confidence`: triage ranking 0–1, not p(compromise)
- Power BI `confidence_score`: normalized from 0–5 ordinal scale
- Transition confidence bumps with writer proof — still not calibrated probability

Prohibited language: "% chance of attack", "probability of malware", "92% confident it's compromised."

Allowed language: "ordinal confidence 0.92 for classification ranking", "higher urgency for human review."

## Alternatives considered

| Alternative | Why rejected |
|-------------|--------------|
| Remove confidence numeric | Loses useful triage sort |
| Train ML classifier with probabilities | No labeled enterprise dataset in scope |
| Rename to `score` only | Breaking change; semantics doc preferred |

## Consequences

- Documentation and interviews must repeat semantics
- FAANG reviewers accept ordinal ranking for prioritization
- Big 4 reviewers accept for triage — not for statistical sampling math

## Security considerations

- Prevents auto-remediation triggered by high "probability"
- Risk committee slides must not imply actuarial precision

## Audit considerations

- Workpapers should quote `limitations[]` alongside confidence
- Do not use confidence alone as control FAIL override

## What this prevents

- Mis-calibrated executive risk heatmaps
- Legal/compliance over-reliance on heuristic scores

## What this does not prove

- Statistical validity of any threshold
- Inter-rater reliability across endpoints

## Interview defense

"0.92 means 'stronger triage signal' in our ordinal model — I don't have labeled malware base rates to calibrate probability, and pretending otherwise would be dishonest in an audit interview."
