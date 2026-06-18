# Business Impact Model

**Module:** `src/platform_core/risk/business_impact.py`

Decision-support estimates for risk triage — **not financial advice** and **not accounting-grade loss estimation**.

## Outputs (ordinal)

| Field | Range | Notes |
|-------|-------|-------|
| `downtime_minutes` | 0+ | Estimate from classification defaults |
| `affected_users` | 0+ | Override via fixture |
| `estimated_cost_per_hour` | USD | Default 150; illustrative only |
| `operational_impact_score` | 1–5 | Ordinal |
| `compliance_impact_score` | 1–5 | Ordinal |
| `reputational_impact_score` | 1–5 | Ordinal |
| `total_business_impact_score` | 1–5 | Mean of dimension scores |
| `confidence_type` | `ordinal_not_probability` | Always |

## API

```python
from src.platform_core.risk.business_impact import estimate_business_impact

estimate_business_impact(classification="DEAD_PROXY_CONFIG")
estimate_business_impact(fixture=case_json)
```

## Limitations

- Classification is not accusation.
- Security-adjacent labels include explicit triage limitations.
- Does not replace business continuity planning or insurance analysis.
