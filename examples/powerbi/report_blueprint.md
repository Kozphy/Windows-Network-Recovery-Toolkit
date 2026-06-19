# Power BI Report Blueprint — Technology Risk Analytics

**Semantic model:** `examples/powerbi/export/` (star schema)  
**Measures:** [dax/measures.md](dax/measures.md)

---

## Page 1: Executive Risk Overview

**Audience:** Risk Committee, CIO, Head of Technology Risk

| Visual | Fields / measure |
|--------|------------------|
| Card | Total Incidents |
| Card | High Risk Incidents |
| Card | Control Failure Rate |
| Line chart | Monthly Incident Trend by `dim_date[month_name]` |
| Stacked bar | `risk_level` by `dim_classification[classification]` |
| Bar chart | Incident count by `dim_classification[classification]` |

**Slicers:** Year, Quarter, `risk_level`

**Interpretation:** High preview-only posture is expected — not a failure to automate.

---

## Page 2: Control Effectiveness

**Audience:** IT Audit, Platform Engineering

| Visual | Fields |
|--------|--------|
| Matrix | `control_name` × `result` (count) |
| Bar | Control Failure Rate by `control_domain` |
| Clustered bar | `evidence_available` by `control_name` |
| Bar | Sum of `limitation_count` by `control_name` |

**Slicers:** `control_domain`, `result`

**Interpretation:** NOT_TESTED is normal for out-of-scope incident classes.

---

## Page 3: Policy Gate & Human Review

**Audience:** IT Operations, Technology Risk

| Visual | Fields |
|--------|--------|
| Donut | `policy_action` distribution |
| Card | Count where `human_confirmation_required = TRUE` |
| Clustered bar | `confirmed` TRUE vs FALSE |
| Table | `blocked_reason`, `incident_id`, `policy_action` |

**Slicers:** `execution_authority`, `policy_action`

**Interpretation:** BLOCK rows indicate safety contracts working — not operational failure.

---

## Page 4: Proof Tier & Evidence Quality

**Audience:** Cyber Risk Consultant, Technology Risk Analyst

| Visual | Fields |
|--------|--------|
| Bar | Incident count by `dim_proof_tier[proof_tier]` |
| Bar | Average Confidence Score by classification |
| Card | Incidents with Limitations |
| Table (drillthrough) | `fact_incidents` detail with dimension labels |

**Slicers:** `proof_tier_key`, `has_limitations`

**Drillthrough:** From any incident visual → detail table with audit_id, created_at, execution_authority

**Interpretation:** T2 does not confirm MITM or malware — see dimension descriptions.

---

## Global elements

- **Footer:** Classification is not accusation. No autonomous remediation.
- **Tooltip page:** Proof tier glossary from `dim_proof_tier`
- **AI transparency card:** AI assists explanation only — does not authorize execution
