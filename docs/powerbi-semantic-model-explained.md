# Power BI Semantic Model Explained

**Status:** Portfolio and PL-300 reference  
**Exporter:** `src/platform_core/analytics/powerbi_star_export.py`  
**Schema version:** `powerbi_star_export.v1`  
**Disclaimer:** Demo seed rows may be included — distinguish portfolio sample from production fleet data.

---

## Purpose

The star schema export transforms audit-backed incident flat files into a **dimensional model** suitable for Microsoft Power BI certification (PL-300) portfolios and technology risk committee dashboards — with columns that **force governance visibility** (`has_limitations`, `is_security_accusation=false`).

---

## Export command

```powershell
python -m windows_network_toolkit powerbi-export `
  --audit-dir tests/fixtures/risk_analytics/audit_sample `
  --out-dir examples/powerbi/export
```

Outputs CSV files under `examples/powerbi/export/` plus README.

---

## Model diagram

```text
                    dim_date
                       │
         ┌─────────────┼─────────────┐
         │             │             │
   dim_classification  │      dim_stakeholder
         │             │             │
         └──────┬──────┴──────┬──────┘
                │             │
           fact_incidents ◄────┘
                │
       ┌────────┴────────┐
       │                 │
fact_control_tests  fact_policy_decisions
       │
  dim_proof_tier (via fact_incidents.proof_tier_key)
```

---

## Fact tables

### fact_incidents

| Column | Type | Description |
|--------|------|-------------|
| `incident_id` | **PK** | Stable incident identifier |
| `audit_id` | Attribute | Source audit bundle reference |
| `date_key` | **FK** → dim_date | YYYYMMDD integer |
| `classification_key` | **FK** → dim_classification | Incident class surrogate key |
| `proof_tier_key` | **FK** → dim_proof_tier | Evidence maturity key |
| `stakeholder_key` | **FK** → dim_stakeholder | Suggested forum audience |
| `risk_level` | Attribute | LOW / MEDIUM / HIGH |
| `confidence_score` | Measure input | Normalized ordinal 0–1 (from confidence_ordinal/5) |
| `execution_authority` | Attribute | preview_only, human_required, … |
| `has_limitations` | Flag | True when limitation_count > 0 |
| `created_at` | Timestamp | Observed_at ISO string |

**Grain:** One row per incident.

---

### fact_control_tests

| Column | Type | Description |
|--------|------|-------------|
| `control_test_id` | **PK** | e.g. `CT-{incident_id}-{control}` |
| `incident_id` | **FK** → fact_incidents | Parent incident |
| `date_key` | **FK** → dim_date | Test date |
| `control_name` | Attribute | Human-readable control name |
| `control_domain` | Attribute | Endpoint Reliability / Platform Governance / Technology Risk Control |
| `result` | Attribute | PASS / FAIL / PARTIAL / NOT_TESTED |
| `evidence_available` | Flag | Whether evidence backed the test |
| `limitation_count` | Integer | Governance caveats count |

**Grain:** One row per incident × control test (derived from `_control_test_rows`).

---

### fact_policy_decisions

| Column | Type | Description |
|--------|------|-------------|
| `decision_id` | **PK** | e.g. `DEC-{incident_id}` |
| `incident_id` | **FK** → fact_incidents | Parent incident |
| `date_key` | **FK** → dim_date | Decision date |
| `policy_action` | Attribute | PREVIEW_ONLY, HUMAN_REVIEW, BLOCK, … |
| `execution_authority` | Attribute | preview_only, human_confirmed, blocked |
| `human_confirmation_required` | Boolean | Typed confirmation needed |
| `confirmed` | Boolean | Operator confirmed apply |
| `blocked_reason` | Text | When policy blocked destructive action |

**Grain:** One row per incident policy decision.

---

## Dimension tables

### dim_classification (PK: classification_key)

| Key | classification | default_risk_level | is_security_accusation |
|-----|----------------|-------------------|------------------------|
| 1 | DEAD_PROXY_CONFIG | MEDIUM | false |
| 2 | WININET_WINHTTP_MISMATCH | MEDIUM | false |
| 3 | LOCAL_PROXY_ACTIVE | LOW | false |
| 4 | UNKNOWN_LOCAL_PROXY | HIGH | false |
| 5 | PAC_CONFIGURED | MEDIUM | false |
| 6 | POSSIBLE_MITM_RISK | HIGH | false |
| 7 | REVERTER_SUSPECTED | HIGH | false |
| 8 | ERROR_INSUFFICIENT_DATA | LOW | false |
| 9 | NO_PROXY | LOW | false |
| 10 | UNCLASSIFIED | MEDIUM | false |

**Design intent:** `is_security_accusation` should remain false for all platform labels — triage ≠ accusation.

---

### dim_proof_tier (PK: proof_tier_key)

| Key | proof_tier | maturity_order |
|-----|------------|----------------|
| 0 | T0_OBSERVATION_ONLY | 0 |
| 1 | T1_LOCAL_CONFIG_EVIDENCE | 1 |
| 2 | T2_RUNTIME_CORROBORATION | 2 |
| 3 | T3_BEHAVIORAL_REPRODUCTION | 3 |
| 4 | T4_OPERATOR_CONFIRMED | 4 |

Use `maturity_order` for sorting — not as probability.

---

### dim_stakeholder (PK: stakeholder_key)

Maps incidents to forum language (IT Support, Technology Risk, Cyber Risk Triage, Internal Audit, Risk Committee, Platform Governance) via `map_business_impact`.

---

### dim_date (PK: date_key)

Standard date spine: `date`, `year`, `quarter`, `month`, `month_name`, `week`, `day`. Mark as date table in Power BI.

---

## Relationships (recommended)

| From | To | Cardinality |
|------|-----|-------------|
| fact_incidents.date_key | dim_date.date_key | Many-to-one |
| fact_incidents.classification_key | dim_classification.classification_key | Many-to-one |
| fact_incidents.proof_tier_key | dim_proof_tier.proof_tier_key | Many-to-one |
| fact_incidents.stakeholder_key | dim_stakeholder.stakeholder_key | Many-to-one |
| fact_control_tests.incident_id | fact_incidents.incident_id | Many-to-one |
| fact_policy_decisions.incident_id | fact_incidents.incident_id | Many-to-one |

Single-direction filters from dimensions to facts.

---

## DAX examples

### Incident volume

```dax
Total Incidents = COUNTROWS ( fact_incidents )
```

### High-risk incidents

```dax
High Risk Incidents =
CALCULATE (
    COUNTROWS ( fact_incidents ),
    fact_incidents[risk_level] = "HIGH"
)
```

### Control failure rate

```dax
Control Failure Rate =
DIVIDE (
    CALCULATE (
        COUNTROWS ( fact_control_tests ),
        fact_control_tests[result] IN { "FAIL", "PARTIAL" }
    ),
    COUNTROWS ( fact_control_tests ),
    0
)
```

### Preview-only policy rate

```dax
Preview Only Rate =
DIVIDE (
    CALCULATE (
        COUNTROWS ( fact_policy_decisions ),
        fact_policy_decisions[policy_action] = "PREVIEW_ONLY"
    ),
    COUNTROWS ( fact_policy_decisions ),
    0
)
```

### Incidents with limitations (governance visibility)

```dax
Incidents With Limitations =
CALCULATE (
    COUNTROWS ( fact_incidents ),
    fact_incidents[has_limitations] = TRUE ()
)
```

### Average proof maturity

```dax
Avg Proof Maturity =
AVERAGE ( RELATED ( dim_proof_tier[maturity_order] ) )
```

Full library: [examples/powerbi/dax/measures.md](../examples/powerbi/dax/measures.md)

---

## PL-300 mapping

| PL-300 skill area | How this model demonstrates it |
|-------------------|-------------------------------|
| **Prepare data** | CSV import, type enforcement, date table |
| **Model data** | Star schema, surrogate keys, relationships |
| **Visualize** | Risk by classification, control failure trends, policy gates |
| **Analyze DAX** | Failure rates, conditional counts, DIVIDE safe ratios |
| **Manage datasets** | Schema version `powerbi_star_export.v1`, refresh from CLI |
| **Governance** | Disclaimers on every page; limitations tooltips |

**Portfolio tip:** Include one page titled "What this dashboard does NOT prove" listing non-claims from governance report.

---

## Honest limitations

1. **Seed data:** `include_seed=true` merges portfolio sample incidents when audit dir is empty or thin — label dashboards accordingly.
2. **Not real-time:** Export is batch from audit JSONL — not streaming fleet telemetry.
3. **Control catalog split:** Export uses CTRL-EPR-001…006 names; endpoint six-pack uses longer control_id strings — do not double-count as twelve independent controls without mapping.
4. **No RLS in export:** Row-level security design is documented separately ([examples/powerbi/rls_design.md](../examples/powerbi/rls_design.md)) — not enforced in CSV export.
5. **confidence_score is ordinal:** Normalized from 0–5 ordinal — not statistical confidence interval.
6. **MITM label:** `POSSIBLE_MITM_RISK` must not be charted as "confirmed MITM count."
7. **Chain verify coupling:** Export may set proof context from `verify_chain` — invalid chain should block attestation narrative for that period.

---

## Related documents

- [powerbi-schema.md](powerbi-schema.md)
- [examples/powerbi/report_blueprint.md](../examples/powerbi/report_blueprint.md)
- [adr/0005-powerbi-star-schema-design.md](adr/0005-powerbi-star-schema-design.md)
