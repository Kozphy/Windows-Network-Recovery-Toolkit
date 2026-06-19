# ADR-0005: Power BI Star Schema Design

## Status

Accepted

## Context

Portfolio and PL-300 reviewers need dimensional analytics over incidents, controls, and policy decisions — not flat CSV dumps that encourage misleading security charts. Governance caveats must survive into BI layer.

## Decision

Export star schema via `powerbi_star_export.py`:

**Facts:** `fact_incidents`, `fact_control_tests`, `fact_policy_decisions`  
**Dimensions:** `dim_classification`, `dim_proof_tier`, `dim_stakeholder`, `dim_date`

Design choices:

- Surrogate integer keys for classification and proof tier
- `has_limitations` flag on incidents
- `is_security_accusation=false` on all catalog classifications
- `confidence_score` normalized from ordinal — documented as non-probability
- Optional portfolio seed merge when audit dir thin (`include_seed`)
- Schema version `powerbi_star_export.v1`

## Alternatives considered

| Alternative | Why rejected |
|-------------|--------------|
| Single wide denormalized CSV | Poor DAX patterns; duplicate governance text |
| Direct JSON import only | Harder PL-300 portfolio demonstration |
| Omit policy fact table | Hides remediation gate story |

## Consequences

- Two control naming schemes (CTRL-EPR vs endpoint ids) require mapping doc
- Demo dashboards must label seed vs production scope
- RLS documented separately — not in CSV export

## Security considerations

- `SECRET_PATTERN` redaction in exporter
- Do not chart `POSSIBLE_MITM_RISK` as confirmed MITM

## Audit considerations

- Supports committee KPIs — not SOX testing
- Chain verify status should inform whether period is attestation-ready
- Limitation tooltips mandatory on report pages

## What this prevents

- Accidental presentation of triage labels as security accusations
- Hiding control FAIL/PARTIAL mix behind single incident count

## What this does not prove

- Real-time fleet coverage
- Operating effectiveness over full population
- Accuracy of seed/demo rows in portfolio mode

## Interview defense

"I built a star schema so PL-300 reviewers see proper relationships — and I added `has_limitations` and `is_security_accusation=false` so the model fights misleading security dashboards by design."
