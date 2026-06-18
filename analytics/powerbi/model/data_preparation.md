# Data Preparation — JSONL to Power BI CSV

## Pipeline overview

```text
Audit JSONL (*.jsonl)  ──┐
Case study fixtures    ──┼──► analytics-export-powerbi ──► CSV facts + date_dim
risk-assess / control-test ─┘
```

Implementation: `src/platform_core/analytics/powerbi_export.py`

---

## 1. Audit JSONL normalization

**Source:** `tests/fixtures/risk_analytics/audit_sample/*.jsonl` or production `.audit/` directory.

**Steps:**

1. Load all `*.jsonl` files via `_load_audit_records()` (same parser as `risk-kpi-summary`)
2. Skip malformed lines with limitations appended to export metadata
3. Group rows by `incident_id` / `case_id`
4. Derive primary classification from first row with `classification.primary_classification`
5. Map legacy `evidence_tier` (observation / correlation / proof) to proof tiers T0–T4
6. Verify hash chain via `verify_chain()` → `hash_chain_valid` column
7. Emit one `fact_incidents` row per incident group

**Audit events:** One row per JSONL line with `event_type` = `action` or `command` or `observation`.

---

## 2. Classification → fact_incidents

| Source field | CSV column |
|--------------|------------|
| `classification.primary_classification` | `classification` |
| `classification.secondary_signals[]` | `secondary_signals` (pipe-delimited) |
| `classification.confidence` | `confidence_ordinal` (1–5 buckets) |
| `classification.limitations[]` | `limitation_count` |
| `policy_decision.outcome` | `policy_decision` (normalized) |

**Normalization rules:**

| Raw policy outcome | CSV value |
|--------------------|-----------|
| PREVIEW_ONLY | PREVIEW_ONLY |
| REQUIRE_TYPED_CONFIRMATION, REQUIRE_HUMAN_APPROVAL | HUMAN_REVIEW |
| BLOCK, DENY, blocked | BLOCK |
| ALLOW | ALLOW |

Missing classification → `ERROR_INSUFFICIENT_DATA`

---

## 3. Control tests → fact_control_tests

**Source A:** `control-test` CLI / `run_mature_control_tests()` output  
**Source B:** Exporter derives rows from incident classification against CTRL-EPR-001…006 catalog

Each incident generates six control test rows (one per catalog control). Result logic:

| Condition | Result |
|-----------|--------|
| Matching classification | PASS or PARTIAL |
| ERROR_INSUFFICIENT_DATA | NOT_TESTED |
| No match | NOT_TESTED |

---

## 4. date_dim generation

**Function:** `build_date_dim(start, end)`

- Default range: 2026-06-01 to 2026-06-30 (portfolio sample window)
- `date_key` = `YYYYMMDD` integer for relationship to facts
- Includes `fiscal_year` / `fiscal_quarter` (July fiscal year start assumption)

**Power Query alternative:** Generate in Desktop with `Calendar` DAX table — CSV provided for PL-300 “prepare data” evidence.

---

## 5. Null handling

| Situation | Treatment |
|-----------|-----------|
| Missing timestamp | Export timestamp omitted or UTC now (audit rows only) |
| Missing classification | `ERROR_INSUFFICIENT_DATA` |
| Missing policy | `PREVIEW_ONLY` (safe default) |
| Empty evidence_hash | Empty string (not NULL in CSV) |
| Missing secondary signals | Empty string |

---

## 6. Categorical normalization

- All classifications **UPPERCASE** snake case
- Proof tiers: exact enum `T0_OBSERVATION_ONLY` … `T4_OPERATOR_CONFIRMED`
- Risk ratings: `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`
- Booleans: `True` / `False` in CSV (pandas-compatible)

---

## 7. Proof-tier ordering

| Tier | Sort order | Meaning |
|------|------------|---------|
| T0 | 0 | Observation only |
| T1 | 1 | Local config evidence |
| T2 | 2 | Runtime corroboration |
| T3 | 3 | Behavioral reproduction |
| T4 | 4 | Operator confirmed |

Use `dim_proof_tier.tier_order` for sorted visuals — **not** alphabetical sort on tier name.

---

## 8. Risk-rating ordering

| Rating | Sort order |
|--------|------------|
| LOW | 1 |
| MEDIUM | 2 |
| HIGH | 3 |
| CRITICAL | 4 |

Default mapping from classification in exporter (`_RISK_BY_CLASSIFICATION`).

---

## 9. Why confidence is ordinal, not probability

The platform uses `confidence_ordinal` (1–5) because:

1. **Observation ≠ proof** — numeric confidence is a triage aid, not a statistical posterior
2. Fixture and audit evidence are **not** a representative sample for probability estimation
3. PL-300 dashboards should avoid false precision (e.g. “92% chance of malware”)
4. Aligns with `governance.confidence_type = ordinal_not_probability` in CLI JSON

**Power BI tip:** Format as whole number with caption “Ordinal confidence (not probability)”.

---

## CLI commands

```powershell
# Portfolio sample (12 incidents, all classes)
python -m windows_network_toolkit analytics-export-powerbi --portfolio-sample --out-dir analytics/powerbi/data

# From audit + merge seed when sparse
python -m windows_network_toolkit analytics-export-powerbi `
  --audit-dir tests/fixtures/risk_analytics/audit_sample `
  --out-dir analytics/powerbi/exports `
  --include-seed
```
