# Power BI Star Schema

**Canonical schema reference** for technology risk analytics exports.

Detailed column definitions: [model/star_schema.md](model/star_schema.md) · Export commands: [../../docs/powerbi-schema.md](../../docs/powerbi-schema.md)

---

## Tables

| Table | Role |
|-------|------|
| `fact_incidents` | One row per classified incident |
| `fact_evidence` | Evidence events linked to incidents |
| `fact_control_tests` | Control test PASS/FAIL rows |
| `dim_classification` | Primary classification labels |
| `dim_policy` | Policy gate outcomes |
| `dim_proof_tier` | T0–T5 ladder |
| `dim_time` / `dim_date` | Calendar dimension |

Legacy flat export (`analytics-export-powerbi`) writes: `incidents.csv`, `control_tests.csv`, `audit_events.csv`, `remediation_previews.csv`, `risk_decisions.csv`, `date_dim.csv`.

Star export (`powerbi-export`) writes: `fact_*.csv`, `dim_*.csv` under `examples/powerbi/export/`.

Sample CSVs: [sample_csv/](sample_csv/)

---

## Generate samples

```powershell
python -m windows_network_toolkit export-powerbi --audit-dir tests/fixtures/risk_analytics/audit_sample_chained --out-dir analytics/powerbi/sample_csv --include-seed
python -m windows_network_toolkit powerbi-export --audit-dir tests/fixtures/risk_analytics/audit_sample_chained --out-dir examples/powerbi/export
```

Report blueprint: [report_blueprint.md](report_blueprint.md)
