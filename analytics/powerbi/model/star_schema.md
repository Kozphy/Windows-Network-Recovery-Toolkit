# Star Schema — Technology Risk Analytics

## Overview

The semantic model follows a **star schema** optimized for technology risk committee reporting. Facts are at incident, control-test, audit-event, remediation-preview, and risk-decision grain. Dimensions provide calendar, endpoint, classification, proof tier, policy, control, and stakeholder context.

**Model assumption:** One primary `incident_id` per reliability event; multiple child rows in audit and control-test facts.

---

## Fact tables

### fact_incidents

| Column | Type | Description |
|--------|------|-------------|
| incident_id | string (PK) | Unique incident identifier |
| endpoint_id | string (FK → dim_endpoint) | Affected endpoint |
| observed_at | datetime | First classified observation timestamp |
| date_key | int (FK → dim_date) | `YYYYMMDD` for relationship to calendar |
| classification | string (FK → dim_classification) | Primary triage label |
| proof_tier | string (FK → dim_proof_tier) | T0–T4 evidence strength |
| risk_rating | string | LOW / MEDIUM / HIGH / CRITICAL |
| confidence_ordinal | int | 1–5 ordinal confidence (not probability) |
| limitation_count | int | Count of explicit limitations |
| policy_decision | string (FK → dim_policy) | ALLOW / PREVIEW_ONLY / BLOCK / HUMAN_REVIEW |
| execution_authority | string | preview_only / human_confirmed / blocked |
| human_review_required | boolean | Governance queue flag |
| remediation_preview_generated | boolean | Preview emitted |
| hash_chain_valid | boolean | Audit chain verified at export time |
| ai_assisted_explanation | boolean | AI narrative assisted (not authorized action) |
| audit_id | string | Linked audit bundle |

**Grain:** One row per `incident_id`.

**Business meaning:** Endpoint reliability incident snapshot for risk trending and executive KPIs.

---

### fact_control_tests

| Column | Type | Description |
|--------|------|-------------|
| control_test_id | string (PK) | Unique test execution row |
| incident_id | string (FK → fact_incidents) | Parent incident |
| endpoint_id | string (FK → dim_endpoint) | Endpoint under test |
| observed_at | datetime | Test execution time |
| date_key | int (FK → dim_date) | Calendar key |
| control_id | string (FK → dim_control) | Control identifier |
| control_test_result | string | PASS / FAIL / PARTIAL / NOT_TESTED |
| classification | string (FK → dim_classification) | Incident class context |

**Grain:** One row per `control_test_id` (incident × control catalog entry).

**Business meaning:** Design-effectiveness testing for endpoint reliability controls.

---

### fact_audit_events

| Column | Type | Description |
|--------|------|-------------|
| audit_event_id | string (PK) | Unique audit row |
| incident_id | string (FK → fact_incidents) | Parent incident |
| event_type | string | observation, remediation_preview, blocked, etc. |
| policy_decision | string (FK → dim_policy) | Policy at event time |
| dry_run | boolean | Preview vs execute attempt |
| hash_chain_valid | boolean | Chain integrity flag |

**Grain:** One row per append-only audit event exported from JSONL.

**Business meaning:** Immutable-style event trail for auditability dashboards (CSV snapshot limitation documented separately).

---

### fact_remediation_previews

| Column | Type | Description |
|--------|------|-------------|
| preview_id | string (PK) | Unique preview row |
| incident_id | string (FK → fact_incidents) | Parent incident |
| remediation_preview_generated | boolean | Always true in this fact |
| execution_authority | string | Expected preview_only |
| human_review_required | boolean | Review before apply |

**Grain:** One row per remediation preview event.

**Business meaning:** Policy-gated remediation posture — **not** autonomous execution metrics.

---

### fact_risk_decisions

| Column | Type | Description |
|--------|------|-------------|
| risk_decision_id | string (PK) | Decision record identifier |
| incident_id | string (FK → fact_incidents) | Parent incident |
| proof_tier | string (FK → dim_proof_tier) | Evidence tier at decision |
| risk_rating | string | Residual risk ordinal |
| recommended_action | string | Advisory action text |
| evidence_hash | string | Content hash for replay verification |
| human_review_required | boolean | Governance gate |

**Grain:** One row per formal risk decision per incident.

**Business meaning:** Technology risk decision artifact aligned with `RiskDecisionRecord` in the platform.

---

## Dimension tables

### dim_date

**PK:** `date_key` (integer `YYYYMMDD`)

**Grain:** One row per calendar day.

Used for time intelligence: incident volume trends, control pass rate by month, fiscal quarter rollups.

---

### dim_endpoint

| Column | Description |
|--------|-------------|
| endpoint_id (PK) | Synthetic or hostname identifier |
| endpoint_name | Display name |
| business_unit | e.g. Finance, Dev, Security |
| environment | Production / UAT / Dev |

**Source:** Derived from `endpoint_id` prefix in portfolio sample (`EP-FIN-*`, `EP-DEV-*`).

---

### dim_classification

| Column | Description |
|--------|-------------|
| classification (PK) | DEAD_PROXY_CONFIG, WININET_WINHTTP_MISMATCH, … |
| classification_group | Proxy / TLS / Data quality |
| default_risk_rating | Default ordinal risk |
| requires_human_review | Default review flag |
| limitation_note | Non-accusation disclaimer |

---

### dim_proof_tier

| Column | Description |
|--------|-------------|
| proof_tier (PK) | T0_OBSERVATION_ONLY … T4_OPERATOR_CONFIRMED |
| tier_order | 0–4 for sorting |
| tier_label | Business-friendly label |
| max_claim | What this tier does **not** prove |

---

### dim_policy

| Column | Description |
|--------|-------------|
| policy_decision (PK) | ALLOW / PREVIEW_ONLY / BLOCK / HUMAN_REVIEW |
| allows_execution | False for PREVIEW_ONLY and BLOCK |
| requires_confirmation | True for HUMAN_REVIEW paths |

---

### dim_control

| Column | Description |
|--------|-------------|
| control_id (PK) | CTRL-EPR-001 … |
| control_name | Display name |
| control_objective | ITGC-style objective text |
| remediation_owner | Default owner |

---

### dim_stakeholder

| Column | Description |
|--------|-------------|
| stakeholder_id (PK) | IT_SUPPORT, TECH_RISK, CYBER_TRIAGE, AUDIT |
| forum_name | Committee or function |
| suggested_forum_mapping | From business impact mapping |

**Relationship:** Bridge to `dim_classification.suggested_forum` for narrative drill-through.

---

## Relationships (Power BI)

```text
dim_date[date_key] 1──* fact_incidents[date_key]
dim_endpoint[endpoint_id] 1──* fact_incidents[endpoint_id]
dim_classification[classification] 1──* fact_incidents[classification]
dim_proof_tier[proof_tier] 1──* fact_incidents[proof_tier]
dim_policy[policy_decision] 1──* fact_incidents[policy_decision]

fact_incidents[incident_id] 1──* fact_control_tests[incident_id]
fact_incidents[incident_id] 1──* fact_audit_events[incident_id]
fact_incidents[incident_id] 1──* fact_remediation_previews[incident_id]
fact_incidents[incident_id] 1──* fact_risk_decisions[incident_id]

dim_control[control_id] 1──* fact_control_tests[control_id]
dim_policy[policy_decision] 1──* fact_audit_events[policy_decision]
dim_proof_tier[proof_tier] 1──* fact_risk_decisions[proof_tier]
```

**Filter direction:** Single direction from dimensions to facts (except optional bidirectional for stakeholder bridge tables).

**Inactive relationships:** If multiple date columns exist, mark secondary `observed_at` calculated `date_key` as active for time intelligence.

---

## Business rules encoded in the model

1. **High risk** ≠ confirmed compromise — maps to triage severity only  
2. **T3+** = behavioral reproduction tier or higher — still not malware proof  
3. **Preview-only rate** should trend high — indicates safe governance defaults  
4. **Human review pending** = `human_review_required = TRUE` and incident open  
