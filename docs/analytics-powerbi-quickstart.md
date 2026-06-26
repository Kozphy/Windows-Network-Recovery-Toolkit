# Analytics, Power BI, and governance reporting

Quickstart moved from the root README. This is **portfolio-ready** export tooling — not a deployed Power BI Service tenant or formal SOC 2 attestation.

## Commands

```powershell
# Star-schema semantic model pack
python -m windows_network_toolkit powerbi-export `
  --audit-dir tests/fixtures/risk_analytics/audit_sample_chained `
  --out-dir examples/powerbi/export

# Flat CSV export (alias also available)
python -m windows_network_toolkit export-powerbi `
  --audit-dir tests/fixtures/risk_analytics/audit_sample_chained `
  --out-dir analytics/powerbi/sample_csv

# Governance report from audit directory
python -m windows_network_toolkit governance-report `
  --audit-dir tests/fixtures/risk_analytics/audit_sample `
  --format markdown
```

## Documentation

| Doc | Topic |
|-----|-------|
| [../analytics/powerbi/schema.md](../analytics/powerbi/schema.md) | Star-schema tables |
| [../analytics/powerbi/report_blueprint.md](../analytics/powerbi/report_blueprint.md) | Four-page blueprint |
| [control-matrix.md](control-matrix.md) | CTRL-001–010 |
| [powerbi-interview-story.md](powerbi-interview-story.md) | PL-300 skill mapping |
| [../reports/sample_governance_report.md](../reports/sample_governance_report.md) | Sample committee report |
