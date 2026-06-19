# Power BI Schema — Technology Risk Analytics

**Status:** Phase 1  
**Canonical exporters:** `analytics-export` (endpoint CSV) · `powerbi-export` (star schema)

This document consolidates Power BI contracts for the Technology Risk & Control Analytics Platform. Detailed star-schema design also lives in [analytics/powerbi/model/star_schema.md](../analytics/powerbi/model/star_schema.md).

---

## Export commands

```powershell
# Endpoint analytics — incidents, control tests, risk_scores CSV (Phase 1)
python -m windows_network_toolkit analytics-export `
  --fixture tests/fixtures/analytics_pipeline_fixture.json `
  --out reports/analytics

# Star schema semantic model (portfolio)
python -m windows_network_toolkit powerbi-export `
  --audit-dir tests/fixtures/risk_analytics/audit_sample `
  --out-dir examples/powerbi/export
```

Phase 1 `reporting.export_technology_risk_report()` adds:

| File | Content |
|------|---------|
| `risk_scores.json` / `risk_scores.csv` | Typed scoring output per incident |
| `executive_report.json` | Committee-ready KPI bundle |
| `incidents.json`, `control_tests.json` | Pipeline artefacts |
| `incident_classes.csv`, `control_results.csv`, … | Chart-ready aggregates |

---

## Endpoint analytics CSV tables (`analytics-export`)

| CSV | Grain | Key columns |
|-----|-------|-------------|
| `incident_classes.csv` | Aggregate | `incident_class`, `count` |
| `risk_levels.csv` | Aggregate | `risk_level`, `count` |
| `control_results.csv` | Aggregate | `test_result`, `count` |
| `risk_scores.csv` | Incident | `incident_id`, `risk_score`, `risk_level`, `likelihood`, `impact` |
| `timeline.csv` | Time bucket | `bucket`, `event_count` |
| `evidence_tiers.csv` | Aggregate | `evidence_tier`, `count` |
| `top_listener_processes.csv` | Aggregate | `process_name`, `count` (correlation only) |
| `direct_vs_proxy_outcomes.csv` | Aggregate | `outcome`, `count` |

---

## Star schema tables (`powerbi-export`)

| Table | Type | Purpose |
|-------|------|---------|
| `fact_incidents` | Fact | Incident grain with classification and risk rating |
| `fact_control_tests` | Fact | Control test results |
| `fact_audit_events` | Fact | Audit trail events |
| `dim_classification` | Dimension | Incident class labels and definitions |
| `dim_control` | Dimension | Control catalog |
| `dim_evidence_tier` | Dimension | T0–T4 proof tiers |
| `dim_time` | Dimension | Date spine |
| `dim_endpoint` | Dimension | Endpoint identifiers |

DAX measures: [examples/powerbi/dax/measures.md](../examples/powerbi/dax/measures.md)  
Report blueprint: [examples/powerbi/report_blueprint.md](../examples/powerbi/report_blueprint.md)  
RLS design: [examples/powerbi/rls_design.md](../examples/powerbi/rls_design.md)

---

## Warehouse DDL (SQL analytics)

Portfolio warehouse schema: [schemas/analytics_warehouse.sql](../schemas/analytics_warehouse.sql)  
Data model notes: [analytics_data_model.md](analytics_data_model.md)

---

## Power Query guidance

Import CSV from `reports/analytics/` or `examples/powerbi/export/`:

1. Set `incident_class` and `control_id` as dimension keys.  
2. Join `risk_scores` to `incidents` on `incident_id`.  
3. Display `limitations` as tooltip text — never hide governance caveats.  
4. Do not infer malware from `risk_level=HIGH`.

Full walkthrough: [examples/powerbi/power_query_guidance.md](../examples/powerbi/power_query_guidance.md)

---

## Schema versions

| Artefact | Version key |
|----------|-------------|
| Endpoint analytics payload | `endpoint_evidence_analytics.v1` |
| Risk scoring API | `technology_risk_scoring.v1` |
| Executive report | `technology_risk_executive_report.v1` |
| Star schema export | `powerbi_star_export.v1` |
| Audit governance report | `audit_governance_report.v2` |

---

## Governance disclaimer for dashboards

All Power BI pages must include:

> Technology Risk & Control Analytics — observation is not proof; classification is not accusation; not antivirus or autonomous remediation.
