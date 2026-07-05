# Demo Guide — FAANG Engineering & Big 4 Audit Review

**Purpose:** Two reviewer-optimized demo paths with 60-second pitches and command lists  
**Environment:** Windows preferred for live probes; Linux/macOS uses `--fixture` mode  
**Disclaimer:** Portfolio demonstration — not production fleet attestation.

---

## 60-second pitch — FAANG platform engineering

> "Developer laptops lose hours to mystery browser failures that are often dead WinINET localhost proxies — not DNS, not Wi-Fi. This repo is **decision infrastructure**: read-only JSON CLI, canonical engines in `platform_core`, fixture-safe CI, and policy-gated remediation defaults. I can show dead proxy classification with proof, preview-only disable, and hash-chained audit in under three minutes — the same patterns we'd use for internal developer platform reliability tooling."

**Emphasize:** JSON contracts, dry-run defaults, idempotent reads, deterministic fixtures, consolidation map, scale roadmap honesty.

---

## 60-second pitch — Big 4 technology risk / IT audit

> "This platform translates endpoint proxy failure modes into **control tests**, **evidence tiers**, **risk KPIs**, and a **governance report** with explicit non-claims. It separates observation from proof, blocks malware language without writer telemetry, and keeps remediation preview-only until typed confirmation. I'll walk from audit JSONL through control PASS/FAIL, hash chain verify, and Power BI star export — the artifacts you'd discuss in a technology risk committee, not a SOC 2 opinion."

**Emphasize:** CTRL-001…010, limitations on every output, human-review queue, `is_security_accusation=false`, integrity vs truth.

---

## 60-second pitch — mixed panel (FAANG + Big 4)

> "Same evidence pipeline serves platform reliability and technology risk: deterministic classifier evaluation, replay benchmarks for audit reproduction, policy-gated remediation previews, human review for accusatory-adjacent labels, and governance reports with explicit non-claims — not autonomous security verdicts."

---

## Evaluation & governance commands (add to both paths)

```powershell
python -m windows_network_toolkit classifier-benchmark --cases examples/evaluation/classifier_benchmark_sample.json --format markdown
python -m windows_network_toolkit replay-benchmark --cases tests/fixtures/evaluation/replay_cases.jsonl
pytest -q tests/platform_core/evaluation tests/platform_core/governance/test_human_review.py tests/platform_core/ai_risk_analyst/test_explanation_guardrails.py
```

---

## Path A — FAANG platform engineering (≈5 minutes)

### Narrative arc

1. **Reliability problem** — browser broken, WinINET mispointed
2. **Structured diagnosis** — JSON CLI, no silent fixes
3. **Proof envelope** — path contrast, not guesswork
4. **Safe remediation** — dry-run preview
5. **CI contract** — same flow on fixtures in Linux CI

### Commands (in order)

```powershell
# 1. Baseline state (fixture = dead proxy 59081)
python -m windows_network_toolkit proxy-status --fixture tests/fixtures/enert/dead_proxy_59081.json

# 2. Proof-supported diagnosis
python -m windows_network_toolkit diagnose --proof --fixture tests/fixtures/enert/dead_proxy_59081.json

# 3. Health audit shape
python -m windows_network_toolkit proxy-health --fixture tests/fixtures/proxy_health_dead.json

# 4. Control tests
python -m windows_network_toolkit control-test --fixture tests/fixtures/case_studies/case_1_dead_wininet_proxy.json

# 5. Remediation preview (default dry-run)
python -m windows_network_toolkit proxy-disable --dry-run --fixture tests/fixtures/enert/dead_proxy_59081.json

# 6. Analytics pipeline JSON
python -m windows_network_toolkit analytics-summary --fixture tests/fixtures/analytics_pipeline_fixture.json
```

### Live Windows add-on (if available)

```powershell
python -m windows_network_toolkit proxy-status
python -m windows_network_toolkit proxy-health
python -m windows_network_toolkit proxy-owner
```

### Talking points

- Facade → engine separation (`windows_network_toolkit` → `src/platform_core`)
- `proxy_state_machine` uses **full before/after** — interview-grade safety
- Deprecation path for legacy `src/cli.py` modules
- Roadmap: fleet agent, FastAPI, SIEM export — **not claiming today**

---

## Path B — Big 4 audit / technology risk (≈5 minutes)

### Narrative arc

1. **Audit population** — JSONL decision trail
2. **Integrity** — hash chain verify
3. **Controls** — CTRL-001 FAIL on dead proxy with limitations
4. **Governance** — executive summary + human-review queue
5. **Reporting** — Power BI star schema for committee KPIs

### Commands (in order)

```powershell
# 1. Audit integrity
python -m windows_network_toolkit audit verify tests/fixtures/risk_analytics/audit_sample/canonical_decision_audit.jsonl

# 2. Risk KPIs
python -m windows_network_toolkit risk-kpi-summary --audit-dir tests/fixtures/risk_analytics/audit_sample --format markdown

# 3. Governance report (full committee pack)
python -m windows_network_toolkit governance-report --audit-dir tests/fixtures/risk_analytics/audit_sample --format markdown

# 4. Risk assessment on case study
python -m windows_network_toolkit risk-assess --fixture tests/fixtures/case_studies/case_1_dead_wininet_proxy.json

# 5. Power BI export
python -m windows_network_toolkit powerbi-export --audit-dir tests/fixtures/risk_analytics/audit_sample --out-dir examples/powerbi/export

# 6. Reverter case (human review)
python -m windows_network_toolkit control-test --fixture tests/fixtures/case_studies/case_3_reverter_suspected.json
```

### Case study highlights

| Case | Classification | Control highlight | Limitation to state |
|------|----------------|-------------------|---------------------|
| Dead proxy | `DEAD_PROXY_CONFIG` | CTRL-001 FAIL | Not malware |
| WinHTTP mismatch | `WININET_WINHTTP_MISMATCH` | CTRL-002 FAIL | Alignment ≠ policy approval |
| Reverter | `REVERTER_SUSPECTED` | CTRL-007 FAIL | Correlation — collect E13 |
| Unknown listener | `UNKNOWN_LOCAL_PROXY` | CTRL-006 + human queue | Triage only |

### Talking points

- `limitations_and_non_claims` in governance report
- `unsafe_inferences_blocked` in transition classification
- Control **PARTIAL** on owner without Sysmon — expected, not weakness
- Power BI: `Security Accusation Count` should be **zero**

---

## Combined 3-minute "best of both" (interview crunch)

```powershell
python -m windows_network_toolkit diagnose --proof --fixture tests/fixtures/enert/dead_proxy_59081.json
python -m windows_network_toolkit control-test --fixture tests/fixtures/case_studies/case_1_dead_wininet_proxy.json
python -m windows_network_toolkit proxy-disable --dry-run
python -m windows_network_toolkit governance-report --audit-dir tests/fixtures/risk_analytics/audit_sample --format markdown
```

**Close with:** "Observation ≠ proof; classification ≠ accusation; recommendation ≠ execution authority."

---

## Pre-demo checklist

- [ ] Python env with project installed (`pip install -e .`)
- [ ] Fixture paths exist (run from repo root)
- [ ] For live Windows: admin not required for read-only commands
- [ ] Open `docs/control-matrix.md` for CTRL table reference
- [ ] Open governance report output — scroll to Limitations and Human-review queue
- [ ] Power BI Desktop optional — show CSV + DAX doc if no Desktop

---

## Anticipated reviewer questions

See [anti-code-paste-defense.md](anti-code-paste-defense.md) — all 15 questions with brief answers.

Extended Q&A: [big4_interviewer_q_and_a.md](big4_interviewer_q_and_a.md)

---

## Related documents

- [faang-platform-engineering-positioning.md](faang-platform-engineering-positioning.md)
- [big4_demo_flow.md](big4_demo_flow.md)
- [demo-script.md](demo-script.md)
- [three-minute-demo-script.md](three-minute-demo-script.md)
