# SQL KPI Examples (Risk Analytics)

Load CSV fixtures or ETL from `risk-kpi-summary` JSON into your warehouse.

## Incident count by classification

```sql
SELECT classification, COUNT(*) AS incident_count
FROM incidents
GROUP BY classification
ORDER BY incident_count DESC;
```

## Percentage by evidence tier

```sql
SELECT evidence_tier,
       COUNT(*) * 100.0 / SUM(COUNT(*)) OVER () AS pct
FROM incidents
GROUP BY evidence_tier;
```

## Control failure rate

```sql
SELECT
  SUM(CASE WHEN result = 'FAIL' THEN 1 ELSE 0 END) * 1.0
  / NULLIF(COUNT(*), 0) AS control_failure_rate
FROM control_tests;
```

## Repeat incident trend

```sql
SELECT classification, COUNT(*) AS occurrences
FROM incidents
GROUP BY classification
HAVING COUNT(*) > 1;
```

## High-risk unresolved incidents

```sql
SELECT *
FROM incidents
WHERE status = 'open'
  AND classification IN ('POSSIBLE_MITM_RISK', 'UNKNOWN_LOCAL_PROXY', 'SUSPICIOUS_PROXY');
```

## Average time observation to preview

```sql
-- Requires remediation_actions joined to incidents on incident_id
SELECT AVG(
  EXTRACT(EPOCH FROM (r.timestamp - i.timestamp)) / 60.0
) AS avg_minutes_to_preview
FROM incidents i
JOIN remediation_actions r ON r.incident_id = i.incident_id
WHERE r.action = 'remediation_preview';
```

## Policy decision distribution

```sql
SELECT policy_outcome, COUNT(*) AS cnt
FROM incidents
GROUP BY policy_outcome;
```
