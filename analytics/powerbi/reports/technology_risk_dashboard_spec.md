# Technology Risk Dashboard Specification

Four-page Power BI report design for PL-300 portfolio demonstration.

**Dataset:** `analytics/powerbi/data/*.csv`  
**Model:** See [star_schema.md](../model/star_schema.md)  
**Measures:** See [dax_measures.md](../model/dax_measures.md)

---

## Page 1: Executive Risk Overview

### Target stakeholder
CIO, Head of Technology Risk, IT Steering Committee

### Business question
How many endpoint reliability incidents affect the organization, how severe are they, and are we defaulting to safe remediation posture?

### Visuals

| Visual | Fields |
|--------|--------|
| KPI cards | Total Incidents, High Risk Rate, Preview Only Rate, Human Review Pending |
| Clustered bar | Incidents by `classification` |
| Donut | `risk_rating` distribution |
| Line chart | Incidents by `dim_date[month_name]` |
| Table | Top 10 incidents — classification, proof_tier, policy_decision, human_review_required |

### Filters / slicers
- Date range (`dim_date`)
- `risk_rating`
- `business_unit` (from `dim_endpoint`)
- `policy_decision`

### KPIs
- Total Incidents
- High Risk Rate
- Preview Only Rate
- Policy Block Rate

### Interpretation notes
- Rising **dead proxy** counts often indicate dev-tool cleanup gaps, not security incidents
- High **preview-only rate** is expected and desirable

### Limitations
- Ordinal risk ratings — not financial loss
- Sample data is portfolio-scoped, not enterprise census

---

## Page 2: Evidence & Proof Tier

### Target stakeholder
Technology Risk Analyst, Cyber Risk Consultant

### Business question
Is evidence strength sufficient before escalation or remediation narrative?

### Visuals

| Visual | Fields |
|--------|--------|
| Stacked bar | Incidents by `proof_tier` and `classification` |
| KPI | T3 Plus Evidence Coverage |
| Matrix | classification × proof_tier counts |
| Bar | `confidence_ordinal` average by classification |
| Card | Incidents with Limitations |

### Filters / slicers
- `proof_tier`
- `classification`
- `ai_assisted_explanation`

### KPIs
- T3 Plus Evidence Coverage
- Incidents with Limitations
- AI Assisted Explanation Rate

### Interpretation notes
- **T0–T1** incidents should not drive destructive remediation
- **POSSIBLE_MITM_RISK** capped at T2 in platform rules — visual should not imply confirmed MITM

### Limitations
- Proof tier ≠ compromise confirmation
- AI explanation flag does not increase proof tier

---

## Page 3: Control Testing & Remediation Preview

### Target stakeholder
ITGC / IT Audit, Platform Engineering

### Business question
Are endpoint reliability controls operating as designed, and is remediation staying in preview?

### Visuals

| Visual | Fields |
|--------|--------|
| KPI cards | Control Pass Rate, Control Tests Failed, Preview Only Actions |
| Bar | `control_test_result` by `control_name` |
| Matrix | `control_id` × `classification` with PASS/FAIL counts |
| Line | Remediation previews over time (`fact_remediation_previews`) |
| Table | Failed / PARTIAL control tests with `residual_risk` |

### Filters / slicers
- `control_id`
- `control_test_result`
- `remediation_preview_generated`

### KPIs
- Control Pass Rate
- Control Tests Failed
- Preview Only Rate

### Interpretation notes
- **NOT_TESTED** is normal for out-of-scope classifications
- **PARTIAL** on reverter control indicates need for proxy-watch evidence

### Limitations
- Control tests reflect **design** for fixture scope — not SOX attestation
- No autonomous remediation metrics by design

---

## Page 4: Auditability & Human Review

### Target stakeholder
Internal Audit, Compliance, Security Operations

### Business question
Can we reconstruct decisions, verify audit integrity, and clear the human-review queue?

### Visuals

| Visual | Fields |
|--------|--------|
| KPI | Audit Verification Pass Rate, Human Review Pending |
| Table | Human-review queue — classification, proof_tier, recommended_action |
| Timeline | `fact_audit_events` by `observed_at` |
| Bar | Audit events by `event_type` |
| Card (static) | AI usage transparency + non-claims text |

### Filters / slicers
- `human_review_required`
- `hash_chain_valid`
- `classification` (accusatory-adjacent classes)

### KPIs
- Human Review Pending
- Audit Verification Pass Rate
- Mean Time to Evidence (if audit density supports it)

### Interpretation notes
- `hash_chain_valid = FALSE` should trigger investigation — not silent refresh
- Queue items require analyst sign-off before remediation apply

### Limitations
- CSV export breaks append-only guarantees — link to JSONL source for formal audit
- No regulatory sign-off language on this page

---

## Global report settings

| Setting | Value |
|---------|-------|
| Theme | Corporate light + risk semantic colors (red = high ordinal risk only) |
| Page footer | Governance disclaimer from `governance_and_security.md` |
| Tooltip pages | Proof tier definitions, policy decision glossary |
| Mobile layout | Page 1 KPIs only (optional) |

---

## PL-300 skill mapping

| PL-300 domain | This report |
|---------------|-------------|
| Prepare the data | CSV import, Power Query types, date_key |
| Model the data | Star schema relationships |
| Visualize and analyze | Four stakeholder pages, DAX KPIs |
| Deploy and secure | RLS design doc, refresh assumptions |
