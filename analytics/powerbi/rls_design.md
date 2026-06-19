# Row-Level Security Design — Technology Risk Analytics

**Scope:** Design document for portfolio / PL-300 interview — no authentication implementation in this repository.

**Principle:** Classification is not accusation. RLS separates operational triage from committee rollup without implying malware verdicts.

---

## Role: IT Support

**Purpose:** Diagnose endpoint reliability; view remediation previews.

| Table | Filter |
|-------|--------|
| `fact_incidents` | All rows |
| `fact_policy_decisions` | All rows |
| `fact_control_tests` | `control_domain = "Endpoint Reliability"` |
| `dim_classification` | All rows |

**Cannot:** See aggregated-only executive KPIs (optional hide via object-level security).

---

## Role: Security / Cyber Risk

**Purpose:** Review classifications and proof tiers without accusatory semantics.

| Table | Filter |
|-------|--------|
| `fact_incidents` | All rows |
| `dim_proof_tier` | All rows |
| `dim_classification` | `is_security_accusation = FALSE` |

**DAX filter (illustrative):**

```dax
dim_classification[is_security_accusation] = FALSE ()
```

**Narrative rule:** Dashboards must not label visuals "Malware detected" or "Compromise confirmed."

---

## Role: Audit

**Purpose:** Sample incidents, control tests, and audit trail fields for ITGC-style review.

| Table | Filter |
|-------|--------|
| `fact_incidents` | All rows |
| `fact_control_tests` | All rows |
| `fact_policy_decisions` | All rows |
| `dim_stakeholder` | All rows |

**Emphasis visuals:** Hash chain verification status, control failure interpretation, `limitations[]` counts.

---

## Role: Risk Committee (Executive)

**Purpose:** Aggregated KPIs only — no raw registry paths or host identifiers.

| Table | Filter |
|-------|--------|
| `fact_incidents` | Aggregates via measures; hide detail columns |
| `fact_control_tests` | Summary measures only |
| `dim_date` | All rows |

**Implementation options:**

1. **Dynamic RLS** on `dim_stakeholder[role] = "Executive"`
2. **Separate thin executive semantic model** with pre-aggregated tables from `powerbi-export`

---

## Role: Platform Engineering (FAANG demo)

**Purpose:** Replay determinism and safety contract metrics.

| Table | Filter |
|-------|--------|
| `fact_control_tests` | `control_id` IN { "CTRL-009", "CTRL-010" } OR all rows for engineering sandbox |
| `fact_incidents` | All rows in fixture-backed demo tenant |

---

## Testing RLS in Power BI Desktop

1. **Modeling → Manage roles** — add filters per table above.
2. **View as** — validate IT Support sees control domain slice; Executive sees cards without PII columns.
3. **Document limitations** in report footer: RLS design is portfolio evidence — not production Entra ID integration.

---

## What RLS does not do

- Does not replace policy gates in the CLI (typed confirmation, dry-run default)
- Does not prove data integrity (use `audit verify` for hash chain)
- Does not authorize remediation — read-only analytics layer only
