# Data Risk Analyst Demo

**Audience:** Data / Risk Analyst, IT Risk analytics

## Flow

```text
audit logs → analytics model → SQL KPIs → dashboard summary → risk trend interpretation
```

## Steps

1. **Analytics summary**

```powershell
python -m windows_network_toolkit analytics-summary --audit-dir tests/fixtures/risk_analytics/audit_sample --format markdown
```

2. **Risk KPI rollup**

```powershell
python -m windows_network_toolkit risk-kpi-summary --audit-dir tests/fixtures/risk_analytics/audit_sample --format markdown
```

3. **Data dictionary & SQL**

- [risk_analytics_data_dictionary.md](risk_analytics_data_dictionary.md)
- [sql_kpi_examples.md](sql_kpi_examples.md)
- Fixtures: `tests/fixtures/risk_analytics/*.csv`

4. **Governance report (audit-backed)**

```powershell
python -m windows_network_toolkit governance-report --audit-dir tests/fixtures/risk_analytics/audit_sample --format json
```

## Interpretation guide

| KPI | Healthy signal |
|-----|----------------|
| `remediation_previews_count` | High preview rate = governance culture |
| `control_failure_rate` | Investigate FAIL, not automatic block |
| `repeat_incident_rate` | Recurring DEAD_PROXY_CONFIG → config monitoring gap |
| `mean_time_to_preview_minutes` | Lower = faster policy-gated response |

**Limitation:** Confidence is ordinal (`ordinal_not_probability`), not statistical probability.
