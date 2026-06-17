# SQL Analytics Queries — Risk & Control KPIs

Analyst-ready SQL for **Data Analyst**, **Risk Data Analyst**, **Technology Risk Analyst**, **IT Audit Analytics**, and **Security Data Analyst** interviews.

**Schema:** [analytics_data_model.md](analytics_data_model.md) · **DDL:** [`schemas/analytics_warehouse.sql`](../schemas/analytics_warehouse.sql)

**Note:** Confidence scores are **ordinal (0–1)**, not probabilities. Filter dashboards with `evidence_tier` and `claim_strength` to avoid overstating proof.

---

### Query 1 — Incident count by classification

**Business question:**  
Which endpoint failure patterns occur most often, and where should we focus playbook and control investments?

**SQL:**

```sql
SELECT
    classification,
    COUNT(*) AS incident_count,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS pct_of_total
FROM incidents
GROUP BY classification
ORDER BY incident_count DESC;
```

**Interpretation:**  
High counts for `DEAD_PROXY_CONFIG` suggest reliability-driven L1 volume rather than security incidents. Use this to separate **helpdesk efficiency** work from **escalation** work. Pair with `evidence_tier` — a high count at `observation` only may indicate immature triage.

---

### Query 2 — Evidence maturity distribution

**Business question:**  
What share of incidents reach proof or attribution tier versus stopping at observation?

**SQL:**

```sql
SELECT
    evidence_tier,
    COUNT(*) AS incident_count,
    ROUND(AVG(confidence_score), 3) AS avg_confidence,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS pct_of_incidents
FROM incidents
GROUP BY evidence_tier
ORDER BY CASE evidence_tier
    WHEN 'observation' THEN 1
    WHEN 'correlation' THEN 2
    WHEN 'proof' THEN 3
    WHEN 'attribution' THEN 4
    WHEN 'final_causation' THEN 5
END;
```

**Interpretation:**  
A healthy program shows growing `proof` share for repeat classifications. Heavy `observation` with high `business_impact` is a **control gap** — detective controls or telemetry (Sysmon E13) may be missing. Never treat `avg_confidence` as malware probability.

---

### Query 3 — Policy block rate

**Business question:**  
How often does the policy engine block or gate destructive actions?

**SQL:**

```sql
SELECT
    pd.decision,
    COUNT(*) AS decision_count,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS pct_of_decisions,
    SUM(CASE WHEN pd.blocked_action IS NOT NULL THEN 1 ELSE 0 END) AS with_blocked_action
FROM policy_decisions pd
GROUP BY pd.decision
ORDER BY decision_count DESC;
```

**Interpretation:**  
Strong `PREVIEW_ONLY` and `BLOCK` rates indicate governance culture aligned with dry-run defaults. Sudden drops in blocks after a tooling change may signal **policy regression** — worth audit follow-up.

---

### Query 4 — Audit completeness rate

**Business question:**  
What percentage of closed incidents have a valid hash-chained audit trail?

**SQL:**

```sql
SELECT
    COUNT(DISTINCT i.incident_id) AS closed_incidents,
    COUNT(DISTINCT CASE WHEN ac.hash_chain_valid = TRUE THEN i.incident_id END) AS audit_valid_count,
    ROUND(
        100.0 * COUNT(DISTINCT CASE WHEN ac.hash_chain_valid = TRUE THEN i.incident_id END)
        / NULLIF(COUNT(DISTINCT i.incident_id), 0),
        2
    ) AS audit_completeness_pct
FROM incidents i
LEFT JOIN audit_chain_checks ac ON ac.incident_id = i.incident_id
WHERE i.closed_at IS NOT NULL;
```

**Interpretation:**  
IT Audit and SOX-style reviewers care about **reconstructability**. Below-target completeness means incidents closed without verification — a finding for ITGC incident management. `NULL` audit checks on open incidents are expected.

---

### Query 5 — High-risk endpoint count

**Business question:**  
How many critical endpoints have open high-impact incidents?

**SQL:**

```sql
SELECT
    e.criticality,
    COUNT(DISTINCT e.endpoint_id) AS endpoint_count,
    COUNT(i.incident_id) AS open_incident_count
FROM endpoints e
INNER JOIN incidents i ON i.endpoint_id = e.endpoint_id
WHERE i.closed_at IS NULL
  AND i.business_impact IN ('high', 'critical')
GROUP BY e.criticality
ORDER BY CASE e.criticality
    WHEN 'critical' THEN 1
    WHEN 'high' THEN 2
    WHEN 'medium' THEN 3
    ELSE 4
END;
```

**Interpretation:**  
Concentration of open incidents on `critical` assets drives prioritization for risk committees and FinTech operational resilience reviews. Cross-filter `classification` for security-adjacent patterns (`UNKNOWN_LOCAL_PROXY`, `POSSIBLE_MITM_RISK`).

---

### Query 6 — Top recurring endpoint risks

**Business question:**  
Which endpoints generate repeat incidents (chronic drift or reverter behavior)?

**SQL:**

```sql
SELECT
    e.endpoint_id,
    e.hostname,
    e.owner_team,
    e.criticality,
    COUNT(i.incident_id) AS incident_count,
    COUNT(DISTINCT i.classification) AS distinct_classifications,
    MAX(i.created_at) AS last_incident_at
FROM endpoints e
INNER JOIN incidents i ON i.endpoint_id = e.endpoint_id
GROUP BY e.endpoint_id, e.hostname, e.owner_team, e.criticality
HAVING COUNT(i.incident_id) >= 2
ORDER BY incident_count DESC, e.criticality DESC
LIMIT 20;
```

**Interpretation:**  
Repeat offenders may indicate **reverter processes**, broken golden images, or users with local admin. This query supports **root-cause analytics** without claiming malware — correlate with `REVERTER_SUSPECTED` classifications in a filtered view.

---

### Query 7 — Low confidence but high business impact

**Business question:**  
Where are we making high-stakes decisions with weak evidence (audit exception candidates)?

**SQL:**

```sql
SELECT
    i.incident_id,
    e.hostname,
    i.classification,
    i.confidence_score,
    i.evidence_tier,
    i.business_impact,
    i.policy_decision,
    i.remediation_status
FROM incidents i
INNER JOIN endpoints e ON e.endpoint_id = i.endpoint_id
WHERE i.business_impact IN ('high', 'critical')
  AND (i.confidence_score < 0.5 OR i.evidence_tier IN ('observation', 'correlation'))
  AND i.closed_at IS NULL
ORDER BY i.business_impact DESC, i.confidence_score ASC;
```

**Interpretation:**  
Classic **risk analytics exception report** for Internal Audit. These rows should trigger escalation or more telemetry — not autonomous remediation. Demonstrates epistemic discipline in SQL filters.

---

### Query 8 — Control test pass/fail summary

**Business question:**  
Are detective and preventive controls operating effectively across incidents?

**SQL:**

```sql
SELECT
    ct.control_name,
    ct.control_objective,
    ct.pass_fail,
    COUNT(*) AS test_count,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (PARTITION BY ct.control_name), 2) AS pct_within_control
FROM control_tests ct
GROUP BY ct.control_name, ct.control_objective, ct.pass_fail
ORDER BY ct.control_name, ct.pass_fail;
```

**Interpretation:**  
Expected `FAIL` on drift detection when incidents exist — the control **detected** the issue. `FAIL` on remediation safety or audit trail is a **governance finding**. `NOT_TESTED` rows highlight coverage gaps in the control testing program.

---

### Query 9 — Remediation preview vs execution count

**Business question:**  
Is remediation staying preview-only (safe default), or are applies increasing?

**SQL:**

```sql
SELECT
    proposed_action,
    SUM(CASE WHEN dry_run = TRUE AND executed = FALSE THEN 1 ELSE 0 END) AS preview_only_count,
    SUM(CASE WHEN executed = TRUE THEN 1 ELSE 0 END) AS executed_count,
    SUM(CASE WHEN typed_confirmation_required = TRUE THEN 1 ELSE 0 END) AS confirmation_required_count,
    ROUND(
        100.0 * SUM(CASE WHEN executed = TRUE THEN 1 ELSE 0 END)
        / NULLIF(COUNT(*), 0),
        2
    ) AS execution_rate_pct
FROM remediation_previews
GROUP BY proposed_action
ORDER BY preview_only_count DESC;
```

**Interpretation:**  
Low `execution_rate_pct` is **desired** for a preview-first platform. Spikes in `executed_count` without matching `confirmation_required_count` would indicate a safety regression — flag for platform engineering and IT Risk.

---

### Query 10 — Incidents missing proof evidence

**Business question:**  
Which incidents lack proof-tier evidence events despite being classified?

**SQL:**

```sql
SELECT
    i.incident_id,
    i.classification,
    i.evidence_tier,
    i.confidence_score,
    i.created_at,
    MAX(CASE WHEN ee.claim_strength = 'proof' THEN 1 ELSE 0 END) AS has_proof_event
FROM incidents i
LEFT JOIN evidence_events ee ON ee.incident_id = i.incident_id
GROUP BY i.incident_id, i.classification, i.evidence_tier, i.confidence_score, i.created_at
HAVING MAX(CASE WHEN ee.claim_strength = 'proof' THEN 1 ELSE 0 END) = 0
   AND i.evidence_tier IN ('proof', 'attribution', 'final_causation')
ORDER BY i.created_at DESC;
```

**Interpretation:**  
Returns **data quality exceptions** — incident tier claims proof but no proof events exist. Critical for audit analytics: fixes ETL or downgrades inflated tiers. Empty result set means model integrity is good.

---

### Query 11 — Mean time to diagnosis

**Business question:**  
How fast are we moving from incident open to completed structured diagnosis?

**SQL:**

```sql
SELECT
    i.classification,
    COUNT(*) AS diagnosed_incidents,
    ROUND(AVG(
        EXTRACT(EPOCH FROM (i.diagnosis_completed_at - i.diagnosis_started_at)) / 60.0
    ), 2) AS avg_diagnosis_minutes,
    ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (
        ORDER BY EXTRACT(EPOCH FROM (i.diagnosis_completed_at - i.diagnosis_started_at)) / 60.0
    ), 2) AS median_diagnosis_minutes
FROM incidents i
WHERE i.diagnosis_started_at IS NOT NULL
  AND i.diagnosis_completed_at IS NOT NULL
GROUP BY i.classification
ORDER BY avg_diagnosis_minutes DESC;
```

**Interpretation:**  
Operational efficiency KPI for SRE and IT support leadership. **SQLite variant:** use `(julianday(diagnosis_completed_at) - julianday(diagnosis_started_at)) * 1440` instead of `EXTRACT`. Label dashboards "fixture/prototype MTTD" unless fed by production agents.

---

### Query 12 — Monthly incident trend

**Business question:**  
Are technology risk incidents increasing or decreasing month over month?

**SQL:**

```sql
SELECT
    DATE_TRUNC('month', i.created_at) AS incident_month,
    i.classification,
    COUNT(*) AS incident_count,
    ROUND(AVG(i.confidence_score), 3) AS avg_confidence,
    COUNT(DISTINCT i.endpoint_id) AS affected_endpoints
FROM incidents i
WHERE i.created_at >= DATE_TRUNC('month', CURRENT_TIMESTAMP) - INTERVAL '12 months'
GROUP BY DATE_TRUNC('month', i.created_at), i.classification
ORDER BY incident_month DESC, incident_count DESC;
```

**Interpretation:**  
Trend lines feed **management reporting** and FinTech operational risk committees. Rising `DEAD_PROXY_CONFIG` with stable proof rate may mean onboarding/image issues; rising `UNKNOWN_LOCAL_PROXY` with low confidence warrants security review — not automatic blocking.

**SQLite / BigQuery notes:**

- SQLite: `strftime('%Y-%m', created_at)` instead of `DATE_TRUNC`
- BigQuery: `TIMESTAMP_TRUNC(created_at, MONTH)`

---

## Bonus — Executive KPI single row

**Business question:**  
What is the one-screen risk posture for leadership?

**SQL:**

```sql
SELECT
    (SELECT COUNT(*) FROM incidents WHERE closed_at IS NULL) AS open_incidents,
    (SELECT ROUND(100.0 * AVG(CASE WHEN evidence_tier IN ('proof','attribution','final_causation') THEN 1.0 ELSE 0 END), 1)
     FROM incidents) AS proof_tier_pct,
    (SELECT ROUND(100.0 * AVG(CASE WHEN hash_chain_valid THEN 1.0 ELSE 0 END), 1)
     FROM audit_chain_checks) AS audit_valid_pct,
    (SELECT ROUND(100.0 * SUM(CASE WHEN executed THEN 0 ELSE 1 END) / NULLIF(COUNT(*), 0), 1)
     FROM remediation_previews) AS preview_only_pct
FROM (SELECT 1);
```

**Interpretation:**  
Dashboard headline metrics for portfolio demos. Emphasize `preview_only_pct` near 100% as **intentional governance**, not failure to remediate.

---

## Interview tips

1. Always mention **evidence tier** when presenting confidence aggregates.
2. Pair SQL results with **limitations** from source JSON — analysts sell trust.
3. Reference CLI that produces rows: `risk-assess`, `control-test`, `governance-report`.
4. Offer to show ETL from `proxy-status` → `evidence_events` ([analytics_data_model.md](analytics_data_model.md#6-etl-mapping-platform--warehouse)).

---

## Related

- [analytics_data_model.md](analytics_data_model.md)
- [README_BIG4_PORTFOLIO.md](README_BIG4_PORTFOLIO.md)
- [technology_risk_control_matrix.md](technology_risk_control_matrix.md)
