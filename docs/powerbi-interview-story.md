# Power BI Interview Story (PL-300 Mapping)

Use this script when an interviewer asks how this repository demonstrates **Microsoft Power BI Data Analyst (PL-300)** skills without overclaiming security product capabilities.

---

## 30-second opener

> "I built a deterministic evidence pipeline on Windows endpoints, then exported hash-chained audit JSONL into a **star schema** for technology risk reporting. Power BI is the **read-only committee layer** — incidents, control tests, and policy decisions — not autonomous remediation or malware detection."

---

## PL-300 skill mapping

### 1. Prepare the data

**What you did**

- `python -m windows_network_toolkit powerbi-export --audit-dir tests/fixtures/risk_analytics/audit_sample --out-dir examples/powerbi/export`
- Normalized append-only JSONL into typed CSV facts and dimensions
- Documented refresh assumptions in [examples/powerbi/power_query_guidance.md](../examples/powerbi/power_query_guidance.md)

**Interview line**

> "I treat audit JSONL as the system of record and flatten it into a reproducible star schema — same inputs always yield the same CSV row counts in CI."

**Evidence:** `examples/powerbi/export/README.md`, record counts in CLI JSON output.

---

### 2. Model the data

**What you did**

- Star schema: `fact_incidents`, `fact_control_tests`, `fact_policy_decisions`
- Dimensions: `dim_date`, `dim_classification`, `dim_proof_tier`, `dim_stakeholder`
- Single-direction relationships; `dim_date` as date table

**Interview line**

> "Classifications and proof tiers live in dimensions so KPIs don't fork when incident taxonomy changes — the model encodes 'classification is not accusation' in `dim_classification`."

**Evidence:** [docs/powerbi-semantic-model-explained.md](powerbi-semantic-model-explained.md), [analytics/powerbi/report_blueprint.md](../analytics/powerbi/report_blueprint.md)

---

### 3. Visualize and analyze

**What you did**

- Four-page blueprint: Executive Overview, Risk Trend, Control Testing, Incident Drilldown
- DAX measures for control failure rate, repeat incidents, human confirmation required
- Drillthrough from executive cards to incident limitations

**Interview line**

> "Executive page answers 'how much exposure'; Control Testing page answers 'which controls failed and why that matters for risk' — with explicit failure interpretation, not a pass/fail vanity chart."

**Evidence:** [analytics/powerbi/dax/measures.md](../analytics/powerbi/dax/measures.md)

---

### 4. Manage and secure

**What you did**

- RLS roles: IT Support, Security, Audit, Risk Committee, Platform Engineering
- Footer disclaimers: management information, not formal audit opinion
- No write-back to endpoints from Power BI

**Interview line**

> "RLS separates triage operators from committee rollups. Even with dashboard access, remediation still requires CLI policy gates and typed confirmation."

**Evidence:** [analytics/powerbi/rls_design.md](../analytics/powerbi/rls_design.md)

---

## Demo sequence (3 minutes)

```powershell
# 1. Regenerate export (deterministic)
python -m windows_network_toolkit powerbi-export `
  --audit-dir tests/fixtures/risk_analytics/audit_sample `
  --out-dir examples/powerbi/export

# 2. Show governance narrative source
python -m windows_network_toolkit governance-report `
  --audit-dir tests/fixtures/risk_analytics/audit_sample --format markdown

# 3. Open Power BI Desktop → import CSVs → walk Executive + Control pages
```

---

## Anticipated questions

| Question | Answer |
|----------|--------|
| Is this real-time SIEM? | No — batch export from audit JSONL; portfolio demonstrates semantic modeling. |
| Can users fix proxies from the report? | No — read-only analytics; remediation is preview-only in CLI. |
| Why star schema vs single flat table? | Separate control test grain from incident grain; avoids fan-out on joins. |
| How do you avoid misleading security charts? | `is_security_accusation` dimension + measures that should stay at zero. |

---

## Related docs

- [docs/demo-faang-big4-review.md](demo-faang-big4-review.md) — combined FAANG / Big 4 demo
- [docs/big4-interview-defense.md](big4-interview-defense.md) — why this is not antivirus
- [docs/faang-platform-review.md](faang-platform-review.md) — deterministic replay for engineers
