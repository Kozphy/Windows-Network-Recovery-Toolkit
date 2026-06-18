# Risk Analytics Data Dictionary

Dashboard-ready fields from audit JSONL and portfolio CLI outputs.

## Incident grain (`incidents.csv` fixture)

| Column | Type | Description |
|--------|------|-------------|
| incident_id | string | Unique incident key |
| classification | string | Primary triage label |
| evidence_tier | string | observation / correlation / proof |
| policy_outcome | string | PREVIEW_ONLY, BLOCK, etc. |
| status | string | open / resolved |
| timestamp | ISO8601 | Event time |

## Control test grain (`control_tests.csv`)

| Column | Description |
|--------|-------------|
| control_id | CT-* identifier |
| control_objective | ITGC-style objective |
| result | PASS / FAIL / EXCEPTION / INSUFFICIENT_EVIDENCE |
| incident_id | Linked incident |
| reviewed_at | Review timestamp |

## Remediation grain (`remediation_actions.csv`)

| Column | Description |
|--------|-------------|
| action | remediation_preview / remediation_execute |
| dry_run | true = preview |
| decision | allowed / blocked |
| policy_outcome | Policy gate result |

## KPI JSON (`risk-kpi-summary`)

See `risk_kpi_summary.v1` schema — `kpis.*` keys for warehouse ETL.

**Fixtures:** `tests/fixtures/risk_analytics/`
