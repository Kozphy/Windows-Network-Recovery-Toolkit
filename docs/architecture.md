# Architecture: Technology Risk & Control Analytics Platform

> **Positioning:** Decision infrastructure for endpoint reliability and technology risk — not antivirus, EDR, XDR, or autonomous remediation.

## Layered design

```text
┌─────────────────────────────────────────────────────────────────────────┐
│  Reporting layer — governance reports, KPIs, evidence markdown/HTML    │
├─────────────────────────────────────────────────────────────────────────┤
│  Policy / guardrail layer — PREVIEW_ONLY, typed confirmation, blocks   │
├─────────────────────────────────────────────────────────────────────────┤
│  Proof / testing layer — path contrast, TLS proof, control tests         │
├─────────────────────────────────────────────────────────────────────────┤
│  Classification layer — primary + secondary signals, ordinal confidence│
├─────────────────────────────────────────────────────────────────────────┤
│  Evidence collection layer — WinINET, WinHTTP, listener, timeline      │
├─────────────────────────────────────────────────────────────────────────┤
│  Audit trail layer — append-only hash-chained JSONL                      │
├─────────────────────────────────────────────────────────────────────────┤
│  Replay / verification layer — deterministic fixture replay, CI contracts│
└─────────────────────────────────────────────────────────────────────────┘
```

Canonical implementation: `src/platform_core/` · Windows probes: `src/proxy_guard/`, `windows_network_toolkit/` · API: `backend/`

---

## 1. Evidence collection layer

**Purpose:** Capture observable facts without claiming root cause.

| Source | Signals |
|--------|---------|
| HKCU WinINET registry | ProxyEnable, ProxyServer, PAC URL |
| WinHTTP (`netsh`) | Direct vs proxy configuration |
| Listener probes | localhost port owner (correlation) |
| Network probes | DNS, TCP, HTTP direct vs proxied |
| Telemetry (optional) | Sysmon E13 registry writes |

**Modules:** `windows_network_toolkit/proxy_state.py`, `src/proxy_guard/`, `src/platform_core/attribution/`

**May claim:** State at time T, probe pass/fail  
**Must not claim:** Malware, confirmed MITM, registry writer without proof tier

---

## 2. Classification layer

**Purpose:** Triage incidents into reviewable labels with secondary signals.

| Primary examples | Meaning |
|------------------|---------|
| `NO_PROXY` | Nominal proxy path |
| `DEAD_PROXY_CONFIG` | Proxy enabled, listener dead |
| `LOCAL_PROXY_ACTIVE` | Active localhost listener |
| `REVERTER_SUSPECTED` | Settings flip after disable |
| `POSSIBLE_MITM_RISK` | TLS/path divergence — triage only |

**Module:** `src/platform_core/classification/engine.py`

**Principle:** Classification is not accusation.

---

## 3. Proof / testing layer

**Purpose:** Upgrade claim strength from observation to supported proof for narrow hypotheses.

| Check | Output |
|-------|--------|
| `diagnose --proof` | Proof envelope + limitations |
| `proxy-proof` | Direct vs system-proxy HTTP contrast |
| `tls-proof` | Certificate metadata contrast |
| `control-test` | PASS/FAIL/INSUFFICIENT_EVIDENCE |

**Modules:** `src/platform_core/proof/`, `src/platform_core/tls/`, `src/platform_core/controls/`

**Principle:** Observation is not proof.

---

## 4. Policy / guardrail layer

**Purpose:** Gate remediation — preview by default, block destructive verbs.

| Outcome | Meaning |
|---------|---------|
| `PREVIEW_ONLY` | Show action; do not execute |
| `REQUIRE_HUMAN_APPROVAL` | Escalate before change |
| `BLOCK` | Destructive or low-confidence path denied |

**Modules:** `src/platform_core/policy/`, `platform_core/policy/`, `windows_network_toolkit/safety.py`

**Principle:** Policy permission is not a safety guarantee.

---

## 5. Reporting layer

**Purpose:** Audit-ready narratives for risk, compliance, and operations.

| Output | Command / API |
|--------|----------------|
| Evidence timeline report | `evidence-report` |
| Governance report | `governance-report` |
| Risk KPI rollup | `risk-kpi-summary` |
| Technology risk assessment | `risk-assess` |
| Endpoint analytics + risk scores | `analytics-summary`, `analytics-export` |
| Executive JSON report | `GET /reports/executive` |
| Risk scores API | `GET /risks` |

**Modules:** `windows_network_toolkit/reporting.py`, `windows_network_toolkit/risk_scoring_engine.py`, `src/platform_core/evidence_report/`, `src/platform_core/governance/`, `src/platform_core/risk/`

**Phase 1 flow:**

```text
analytics_pipeline → risk_scoring_engine → reporting → JSON/CSV/Power BI
```

See: [risk-model.md](risk-model.md) · [powerbi-schema.md](powerbi-schema.md)

---

## 6. Audit trail layer

**Purpose:** Append-only, hash-chained records for every read, preview, and mutation attempt.

| Store | Content |
|-------|---------|
| `.audit/*.jsonl` | proxy-status, proxy-disable, proxy-watch |
| `logs/canonical_decision_audit.jsonl` | Platform decisions |
| Risk analytics fixtures | Incident KPI source |

**Modules:** `src/platform_core/audit/`, `windows_network_toolkit/audit_store.py`

Verify: `python -m windows_network_toolkit audit verify <file.jsonl>`

---

## 7. Replay / verification layer

**Purpose:** Deterministic re-run from fixtures — CI safety contracts, interview demos.

| Entry | Behavior |
|-------|----------|
| `replay` / `demo-scenario` | JSONL fixture → timeline + policy |
| `replay-certify` | Hash certification |
| Pytest contracts | Dry-run default, no silent kill, evidence tiers |

**Modules:** `src/platform_core/replay/`, `windows_network_toolkit/audit/replay.py`

---

## Evidence-to-action flow

```text
Collect → Classify → Prove (optional) → Rate risk → Policy gate → Preview → Audit → Report
```

Governance envelope: `evidence_to_action.v1` — see [evidence_to_action_governance_model.md](evidence_to_action_governance_model.md).

---

## AI-assisted layer (advisory)

Optional explanation and report summarization via `src/platform_core/ai_risk_analyst/` — **recommendations only**, never execution. See [ai-assisted-delivery.md](ai-assisted-delivery.md).

---

## Related documentation

- [evidence_model.md](evidence_model.md) · [policy_model.md](policy_model.md) · [control-matrix.md](control-matrix.md)
- [framework_mapping.md](framework_mapping.md) · [PORTFOLIO.md](../PORTFOLIO.md)
