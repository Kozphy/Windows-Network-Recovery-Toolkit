# Power BI Analytics Layer (PL-300 Portfolio)

This folder contains a **Power BI-ready analytics layer** for the Technology Risk & Control Analytics Platform. It demonstrates Microsoft PL-300 skills across prepare, model, visualize, and govern — using CSV exports that mirror the platform’s incident, control, audit, and risk-decision artifacts.

> **Honest positioning:** This is a portfolio-ready semantic model and dashboard **specification**, not a published Power BI Service tenant deployment.

## Contents

| Path | Purpose |
|------|---------|
| `data/` | Sample CSV fact and dimension tables |
| `model/star_schema.md` | Star schema design (facts + dimensions) |
| `model/dax_measures.md` | KPI measures for executive reporting |
| `model/data_preparation.md` | JSONL → CSV normalization pipeline |
| `model/governance_and_security.md` | RLS, refresh, AI boundaries |
| `reports/technology_risk_dashboard_spec.md` | Four-page dashboard specification |
| `exports/` | Target folder for CLI export output |

## Quick start

```powershell
pip install -e ".[dev]"
$env:PYTHONPATH = (Get-Location).Path

# Regenerate portfolio sample CSVs
python -m windows_network_toolkit analytics-export-powerbi --portfolio-sample --out-dir analytics/powerbi/data

# Export from audit JSONL (merges seed when sparse)
python -m windows_network_toolkit analytics-export-powerbi `
  --audit-dir tests/fixtures/risk_analytics/audit_sample `
  --out-dir analytics/powerbi/exports `
  --include-seed
```

## Import into Power BI Desktop

1. Open Power BI Desktop → **Get data** → **Text/CSV**
2. Load all files from `data/` (or `exports/` after CLI run)
3. Apply relationships per `model/star_schema.md`
4. Create measures from `model/dax_measures.md`
5. Build pages per `reports/technology_risk_dashboard_spec.md`

## Governance reminders

- Classification labels are **triage hypotheses**, not malware verdicts
- Proof tiers describe evidence strength — not certainty of compromise
- AI may assist explanation in reports; it does **not** authorize remediation
- CSV exports are snapshots; append-only JSONL remains the custody source of truth

## Related platform commands

| Command | Role |
|---------|------|
| `risk-assess` | Produces `RiskDecisionRecord` JSON |
| `control-test` | Mature control test results |
| `governance-report` | Management narrative + KPI context |
| `risk-kpi-summary` | Audit-backed KPI rollup |
| `analytics-export-powerbi` | CSV export for Power BI |

See also: [README.md](../../README.md) · [PORTFOLIO.md](../../PORTFOLIO.md)
