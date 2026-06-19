# Power BI Analytics Layer (PL-300 Portfolio)

This folder contains a **Power BI-ready analytics layer** for the Technology Risk & Control Analytics Platform. It demonstrates Microsoft PL-300 skills across prepare, model, visualize, and govern — using CSV exports that mirror the platform’s incident, control, audit, and risk-decision artifacts.

> **Honest positioning:** This is a portfolio-ready semantic model and dashboard **specification**, not a published Power BI Service tenant deployment.

## Contents

| Path | Purpose |
|------|---------|
| [report_blueprint.md](report_blueprint.md) | Four-page report spec (Executive, Risk Trend, Control Testing, Drilldown) |
| [dax/measures.md](dax/measures.md) | KPI DAX measures |
| [rls_design.md](rls_design.md) | Row-level security roles |
| `data/` | Legacy sample CSV fact and dimension tables |
| `model/` | Earlier star schema design notes |
| `exports/` | Target folder for legacy `analytics-export-powerbi` |

**Canonical star schema export:** `examples/powerbi/export/` via `powerbi-export` (recommended for portfolio demos).

## Quick start

```powershell
pip install -e ".[dev]"
$env:PYTHONPATH = (Get-Location).Path

# Primary — star schema from fixture audit (deterministic)
python -m windows_network_toolkit powerbi-export `
  --audit-dir tests/fixtures/risk_analytics/audit_sample `
  --out-dir examples/powerbi/export

# Legacy flat CSV export (still supported)
python -m windows_network_toolkit analytics-export-powerbi --portfolio-sample --out-dir analytics/powerbi/data
```

## Import into Power BI Desktop

1. Open Power BI Desktop → **Get data** → **Text/CSV**
2. Load all files from `examples/powerbi/export/` (after `powerbi-export`)
3. Apply relationships per [docs/powerbi-semantic-model-explained.md](../../docs/powerbi-semantic-model-explained.md)
4. Create measures from [dax/measures.md](dax/measures.md)
5. Build pages per [report_blueprint.md](report_blueprint.md)
6. Configure RLS per [rls_design.md](rls_design.md)

**Interview script:** [docs/powerbi-interview-story.md](../../docs/powerbi-interview-story.md)

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
