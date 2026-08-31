# KPI Framework

**Platform:** Technology Risk & Control Analytics for Windows endpoints
**Principle:** Differentiate **current measurable metrics** (from code/tests) from **proposed production KPIs** (if deployed at scale)

**No fabricated achieved values.**

---

## Operational KPIs

| KPI | Definition | Current (portfolio) | Proposed (production) |
|-----|------------|---------------------|------------------------|
| **MTTD** (Mean Time to Detect) | Time from symptom to classified label | Manual CLI timing in demos | Guardian / watch JSONL timestamps |
| **MTTR** (Mean Time to Remediate) | Time from classify to verified fix | Not centrally measured | Ticket + audit correlation |
| **Incident recurrence rate** | Same classification within N days | Fixture replay only | Fleet analytics warehouse |
| **Exception rate** | Incidents requiring human override | Purple `SAFETY_DENIED` count | Override audit events |
| **Automation coverage** | % diagnostics run via structured CLI vs ad-hoc scripts | Qualitative — CLI exists | Fleet agent adoption % |

**Implemented hooks:** `analytics-summary` CLI, purple benchmark metrics, proxy-watch JSONL.

---

## Risk KPIs

| KPI | Definition | Current | Proposed |
|-----|------------|---------|----------|
| **Control failure rate** | CTRL tests FAIL / total | Per governance report | Fleet rollup |
| **Unresolved high-risk exceptions** | OPEN RISK-* without remediation | Sample register | GRC integration |
| **Policy override rate** | Applies with confirmation / total applies | Audit `confirmation_supplied` | SIEM dashboard |
| **Recurring incident rate** | Repeat DEAD_PROXY within window | Replay benchmark | Endpoint trend |

**Implemented hooks:** [control-matrix.md](control-matrix.md), [risk-register.md](risk-register.md).

---

## Engineering KPIs

| KPI | Definition | Current measurable value | Source |
|-----|------------|--------------------------|--------|
| **Test count** | pytest cases | ~333 test files | `tests/` |
| **Safety contract pass rate** | CI policy tests | 100% required on merge | `.github/workflows/ci.yml` |
| **Replay determinism rate** | Classifier replay stability | CI gate ≥ 1.0 | `replay-benchmark` job |
| **Primary classifier match rate** | Fixture regression | CI gate ≥ 0.85 | eval-benchmarks job |
| **Unsafe classification rate** | Accusatory language / blocked labels | CI gate ≤ 0.0 | safety contracts |
| **Purple benchmark smoke** | Pipeline completes | CI job pass | `src.purple_team benchmark` |
| **False positive rate (purple)** | Benign scenario alerts | Benchmark FPR metric | `src/purple_team/evaluation/` |
| **False negative rate (purple)** | Missed detections | Benchmark FNR metric | Same |

---

## Governance KPIs

| KPI | Definition | Current | Proposed |
|-----|------------|---------|----------|
| **Approval turnaround** | Preview → confirmed apply | Not measured | Workflow timestamps |
| **Evidence completeness** | Required fields in custody record | Schema validation tests | Automated audit QA |
| **Traceable decision %** | Decisions with hash-chained record | Qualitative — writer exists | % exports with verified chain |
| **Remediation verification success** | Post-apply verify pass | `verify_proxy_disabled()` | Fleet verify job success |

---

## Purple Team / control validation KPIs

| KPI | Definition | Current |
|-----|------------|---------|
| **Precision** | TP / (TP + FP) | Benchmark output |
| **Recall** | TP / (TP + FN) | Benchmark output |
| **F1** | Harmonic mean | Benchmark output |
| **MTTD (simulated)** | Sim → detect latency | Scenario metrics |
| **Safety denial rate** | Gate blocks / runs | Pipeline state DENIED |

Run: `python -m src.purple_team benchmark --no-evidence --json`

---

## KPI anti-patterns (do not claim)

| Do not claim | Instead say |
|--------------|-------------|
| "Reduced outages by 40%" | "Designed to reduce MTTR via structured preview" |
| "Zero false positives" | "CI gates cap unsafe classification rate at 0" |
| "Audit-ready certification" | "Designed to support control evidence generation" |
| "AI accuracy 95%" | "Rule-based classifier with ordinal confidence" |

---

## Measurement implementation map

| KPI category | Code / doc path |
|--------------|-----------------|
| Operational rollup | `windows_network_toolkit` analytics-summary |
| Control tests | `control_tests.py`, governance-report |
| Audit integrity | `audit verify`, `test_audit_contract.py` |
| Purple metrics | `src/purple_team/evaluation/` |
| SLO framing | [slo-endpoint-reliability.md](slo-endpoint-reliability.md) |
