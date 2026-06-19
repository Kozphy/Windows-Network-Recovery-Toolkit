# Domain Model — Windows Network Recovery Toolkit / Technology Risk Platform

**Status:** Normative reference for engineers, auditors, and risk stakeholders  
**Scope:** Core entities from `windows_network_toolkit/` and `src/platform_core/`  
**Disclaimer:** Entity definitions describe what the platform **records and evaluates** — not regulatory attestation or malware verdicts.

---

## Overview

The platform converts endpoint observations into governed artifacts: normalized evidence, classified incidents, control test results, policy decisions, and exportable analytics. Every entity carries explicit **limitations** so consumers cannot silently upgrade observation to proof.

```text
CLI / proxy-watch
    → EvidenceEvent (normalize)
    → IncidentRecord / ProxyTransition
    → ControlTestResult + RiskAssessment
    → PolicyDecision + RemediationPreview
    → AuditRecord → GovernanceReport → Power BI star schema
```

---

## EvidenceEvent

**Module:** `windows_network_toolkit/evidence_schema.py`

### Purpose

Canonical normalized row for analytics, classification, and export. Preserves `raw_snapshot` for deterministic replay while exposing stable `normalized_fields` for charts and control tests.

### Input / output fields

| Field | Direction | Description |
|-------|-----------|-------------|
| `event_id` | Output | Deterministic SHA-256 hash (24 hex) from timestamp, type, stable fields |
| `timestamp_utc` | Input/Output | ISO-8601 UTC observation time |
| `endpoint_id` | Input/Output | Host identifier; defaults via `default_endpoint_id()` |
| `evidence_type` | Input/Output | `proxy_state`, `listener_state`, `probe_result`, `proxy_change`, … |
| `source_command` | Input | CLI command that produced the row (`proxy-status`, `proxy-health`, …) |
| `raw_snapshot` | Input | Unmodified source dict |
| `normalized_fields` | Output | Classifier/chart fields (e.g. `wininet_proxy_enabled`, `proxy_probe_ok`) |
| `evidence_tier` | Output | T0–T5 claim strength label |
| `evidence_summary` | Output | One-line human summary |
| `limitations` | Output | Governance caveats; `STANDARD_LIMITATIONS` appended where applicable |

### Invariants

- `event_id` is deterministic — same stable inputs produce the same id.
- Normalizers do **not** invent probe results; missing optional fields become empty/false.
- Duplicate `event_id` values are deduplicated in `analytics_pipeline._dedupe_events`.
- Evidence tier labels **do not** auto-upgrade when downstream logic runs.

### Failure modes

- Missing timestamp → empty string; downstream may reject or classify as insufficient data.
- Malformed raw dict → partial normalization; limitations remain attached.
- Cross-host replay without `endpoint_id` → conflated endpoint grain in analytics.

### What it proves

- That a specific command produced a specific observation at a specific time, with preserved raw payload for replay.

### What it does NOT prove

- Registry writer identity, malware presence, MITM confirmation, or that remediation is authorized.

---

## ProxyState

**Module:** `windows_network_toolkit/proxy_state_machine.py` (`ProxyWininetState`)

### Purpose

Comparable WinINET (and optional WinHTTP) configuration snapshot for transition classification and safety validation.

### Input / output fields

| Field | Description |
|-------|-------------|
| `proxy_enable` | WinINET ProxyEnable (bool) |
| `proxy_server` | ProxyServer string or null |
| `auto_config_url` | PAC URL or null |
| `auto_detect` | Auto-detect flag |
| `proxy_override` | ProxyOverride string |
| `parsed_host` / `parsed_port` | Parsed localhost proxy components |
| `proxy_mode` | `DISABLED`, `LOCALHOST_PROXY`, `REMOTE_PROXY`, `PAC_CONFIGURED`, `INCONSISTENT`, … |
| `winhttp_direct_access` | WinHTTP direct-access flag when present |

### Invariants

- `normalize_proxy_state()` accepts registry-facing or toolkit dict key aliases.
- Empty server string is treated as null — never inferred as remote proxy.
- `FORBIDDEN_CLASSIFICATIONS_WHEN_AFTER_SERVER_EMPTY` blocks remote-proxy labels when server is empty.

### Failure modes

- Partial registry read → `UNKNOWN` or `INCONSISTENT` mode.
- Malformed ProxyServer with enable=1 → `INCONSISTENT`.

### What it proves

- Point-in-time WinINET/WinHTTP configuration as read by the toolkit.

### What it does NOT prove

- Who wrote the settings, whether the configuration is authorized, or whether traffic is actually routed as configured.

---

## ProxyTransition

**Module:** `windows_network_toolkit/proxy_state_machine.py` (`build_proxy_evidence_event`, `TransitionClass`)

### Purpose

Audit-grade before/after transition with classification, risk, attribution, and policy hint — derived from **full state**, never isolated field diffs.

### Input / output fields

| Field | Description |
|-------|-------------|
| `event_id` | Hash from timestamp + before + after states |
| `before_state` / `after_state` | Normalized `ProxyWininetState` dicts |
| `transition_class` | e.g. `LOCALHOST_PROXY_ENABLED`, `PROXY_SERVER_REMOVED`, `REVERTER_SUSPECTED_LOCALHOST_PROXY_LOOP` |
| `primary_classification` | Interview-grade label (e.g. `LOCALHOST_PROXY_CONFIGURED`, `REVERTER_SUSPECTED`) |
| `secondary_signals` | e.g. `LISTENER_PRESENT`, `DIRECT_OK_PROXY_FAIL`, `REGISTRY_WRITER_PROOF_UNAVAILABLE` |
| `risk` | Ordinal band: INFO, LOW, MEDIUM, HIGH |
| `confidence` | Ordinal 0–1 (`confidence_semantics: ordinal_not_probability`) |
| `proof_tier` | T0–T3 within state machine (T4 writer proof when telemetry present) |
| `attribution` | `kind`: `correlation`, `none`, or writer proof kinds |
| `evidence` | Human-readable transition lines |
| `limitations` | Transition-specific caveats |
| `recommended_action` | Observe / alert / require human review |
| `policy_decision` | `OBSERVE`, `ALERT`, `REQUIRE_HUMAN_REVIEW` |
| `classification` | Full explainable bundle with `unsafe_inferences_blocked` |

### Invariants

- Classification uses full before/after comparison via `classify_transition()`.
- Reverter detection (`detect_reverter_loop_pattern`) is correlation-only.
- Coalescing merges sub-events within configurable window (default 1000 ms).

### Failure modes

- Missing before or after → `ERROR_INSUFFICIENT_DATA`.
- Safety violation when empty after_server paired with remote classification → listed in `safety_violations`.

### What it proves

- That WinINET proxy-related fields changed between two observed states, with an audit-safe label for the change pattern.

### What it does NOT prove

- Malicious intent, registry writer PID, or that disabling proxy is safe without separate health/path checks.

---

## ClassificationResult

**Modules:** `proxy_state_machine.build_explainable_classification`, `incident_classifier.IncidentRecord`

### Purpose

Primary triage label with supporting/contradicting evidence, human interpretation, and explicit blocked inferences.

### Input / output fields

**Transition-level (`build_explainable_classification`):**

- `primary_classification`, `secondary_signals`, `confidence`, `why[]`, `limitations[]`
- `recommended_next_checks[]`, `unsafe_inferences_blocked[]`, `safety_violations[]`

**Incident-level (`IncidentRecord`):**

- `incident_id`, `incident_class`, `risk_level`, `confidence`
- `supporting_evidence[]`, `contradicting_evidence[]`
- `recommended_policy_action`, `human_interpretation`

### Invariants

- Classification is **not accusation** — no malware verdict labels.
- Confidence is ordinal, not statistical probability.
- Every incident record includes non-empty `limitations[]`.

### Failure modes

- Insufficient evidence events → `ERROR_INSUFFICIENT_DATA` / `UNKNOWN`.
- Over-reliance on process name → mitigated by `unsafe_inferences_blocked`.

### What it proves

- Which hypothesis best fits the evidence bundle for triage and control scoping.

### What it does NOT prove

- Root cause with legal/regulatory certainty, compromise, or authorization to remediate.

---

## RiskAssessment

**Module:** `windows_network_toolkit/risk_scoring_engine.py`

### Purpose

Ordinal `risk_score` (0–100) and `risk_level` (LOW/MEDIUM/HIGH) for governance dashboards, combining classification, proof tier, control aggregate, and business impact.

### Input / output fields

| Input | Output |
|-------|--------|
| `incident_class`, `proof_level`, `evidence_quality` | `risk_score`, `risk_level` |
| `control_aggregate` (worst of PASS/FAIL/PARTIAL/NOT_TESTED) | `human_review_recommended` |
| `business_impact` | `explanation[]`, `limitations[]` |

### Invariants

- Scores are governance input — not malware probability.
- `human_review_recommended` for HIGH scores or control FAIL aggregates.
- Mandatory `GOVERNANCE_LIMITATIONS` on every result.

### Failure modes

- Stale or incomplete audit JSONL → mis-scoring; limitations must be read before escalation.
- Empty control list → aggregates to NOT_TESTED.

### What it proves

- Relative priority for human review within the platform's scoring model.

### What it does NOT prove

- Financial loss forecast, regulatory breach, or calibrated probability of attack.

---

## ControlTestResult

**Modules:** `windows_network_toolkit/control_tests.py`, `src/platform_core/risk/control_test_mature.py`

### Purpose

Evaluate whether endpoint proxy controls are met for the collected evidence — PASS, FAIL, PARTIAL, or NOT_TESTED.

### Input / output fields

| Field | Description |
|-------|-------------|
| `control_id` | Stable id (endpoint: `WININET_LOCALHOST_PROXY_HEALTH`; mature: `CTRL-EPR-001` …) |
| `control_objective` | Human-readable control statement |
| `test_result` | PASS / FAIL / PARTIAL / NOT_TESTED |
| `risk` | Ordinal triage band for the finding |
| `evidence[]` | Supporting observation strings |
| `limitations[]` | Correlation and proof caveats |
| `recommendation` | Next step — preview-only by default |

### Invariants

- Read-only evaluation — no host mutation.
- FAIL on reverter does **not** authorize process kill.
- PARTIAL on owner verification means T4 writer proof not met.

### Failure modes

- Missing health audit → NOT_TESTED for path-dependent controls.
- Incident-class refinement may adjust outcomes — raw health evidence should be audited separately.

### What it proves

- Design effectiveness for the scoped control objective given available evidence.

### What it does NOT prove

- SOX/ISO attestation, operating effectiveness over a full population, or that remediation succeeded.

---

## PolicyDecision

**Modules:** `proxy_state_machine._policy_decision_for_risk`, governance envelope in `src/platform_core/governance/evidence_to_action.py`

### Purpose

Record what policy **permits** (observe, preview, block, require human review) — distinct from execution.

### Input / output fields

- `policy_action`: e.g. `PREVIEW_ONLY`, `REQUIRE_HUMAN_REVIEW`, `OBSERVE`
- `execution_authority`: `preview_only`, `human_required`, `human_confirmed`, `blocked`
- `human_confirmation_required`, `confirmed`, `blocked_reason`

### Invariants

- Policy permission is not a safety guarantee.
- HIGH/CRITICAL risk → `REQUIRE_HUMAN_REVIEW`.

### What it proves

- That the policy engine evaluated the incident/transition against configured gates.

### What it does NOT prove

- That an operator executed correctly, that change management approved action, or that outcome was verified post-apply.

---

## RemediationPreview

**Modules:** `windows_network_toolkit/proxy_remediation.py`, CLI `proxy-disable --dry-run`

### Purpose

Show intended registry/network mutations and rollback snapshot **before** any live apply.

### Input / output fields

- Planned mutations (ProxyEnable, ProxyServer, …)
- `dry_run: true` by default
- Rollback reference state
- Typed confirmation token required for apply (e.g. `DISABLE_WININET_PROXY`)

### Invariants

- Default dry-run; no silent registry mutation in health pipeline.
- Preview does not kill processes or reset firewall.

### What it proves

- What **would** change if an authorized operator confirmed apply.

### What it does NOT prove

- That apply is safe, complete, or that reverter will not restore settings.

---

## AuditRecord

**Modules:** `windows_network_toolkit/audit_store.py`, `src/platform_core/audit/writer.py`

### Purpose

Append-only JSONL row with hash chain fields for tamper-evident decision replay.

### Input / output fields

| Field | Description |
|-------|-------------|
| `timestamp`, `command`, `action` | What ran |
| `incident_id` / `case_id` | Correlation |
| `classification`, `proof_tier` | Decision context |
| `previous_hash`, `current_hash`, `signature_status` | Chain fields |
| Body fields | Command output snapshot, policy outcome, limitations |

### Invariants

- Hash computed over body excluding chain metadata fields.
- Genesis-linked chain verified by `verify_chain()`.

### What it proves

- Append-order integrity of recorded decisions — no silent tamper between genesis and tip.

### What it does NOT prove

- Truth of observations, absence of off-book actions, or SIEM completeness.

---

## GovernanceReport

**Module:** `src/platform_core/governance/audit_report.py`

### Purpose

Committee-ready aggregation: KPIs, control tests, human-review queue, evidence timeline, business impact, audit chain status.

### Input / output fields

- `executive_summary`, `incident_volume_by_classification`
- `control_test_results`, `control_test_summary`
- `human_review_queue`, `high_risk_unresolved_items`
- `audit_chain_verification`, `limitations_and_non_claims`
- `unsafe_inferences_blocked`, `recommended_next_actions`

Schema: `audit_governance_report.v2`

### What it proves

- That audit JSONL in scope was processed into a consistent governance narrative with integrity check.

### What it does NOT prove

- Formal audit opinion, regulatory compliance, or population-wide control operating effectiveness.

---

## Power BI tables

**Module:** `src/platform_core/analytics/powerbi_star_export.py`  
**Export command:** `python -m windows_network_toolkit powerbi-export`

### Fact tables (grain)

| Table | Grain | Primary key |
|-------|-------|-------------|
| `fact_incidents` | One row per incident | `incident_id` |
| `fact_control_tests` | One row per incident × control test | `control_test_id` |
| `fact_policy_decisions` | One row per incident policy decision | `decision_id` |

### Dimension tables

| Table | Primary key | Role |
|-------|-------------|------|
| `dim_classification` | `classification_key` | Incident class labels and default risk |
| `dim_proof_tier` | `proof_tier_key` | T0–T4 maturity ordering |
| `dim_stakeholder` | `stakeholder_key` | Forum / audience mapping |
| `dim_date` | `date_key` | Date spine (YYYYMMDD int) |

### Foreign keys

- `fact_*.date_key` → `dim_date.date_key`
- `fact_incidents.classification_key` → `dim_classification.classification_key`
- `fact_incidents.proof_tier_key` → `dim_proof_tier.proof_tier_key`
- `fact_incidents.stakeholder_key` → `dim_stakeholder.stakeholder_key`
- `fact_control_tests.incident_id` → `fact_incidents.incident_id`
- `fact_policy_decisions.incident_id` → `fact_incidents.incident_id`

### What it proves

- Structured export suitable for PL-300 portfolio dashboards with governance disclaimers.

### What it does NOT prove

- Real-time fleet coverage, malware counts, or attested control effectiveness — seed rows may be included for demo (`include_seed=true`).

---

## Related documents

- [audit-evidence-model.md](audit-evidence-model.md) — T0–T5 tiers and normalization
- [risk-control-framework.md](risk-control-framework.md) — CTRL-001 … CTRL-010
- [control-matrix.md](control-matrix.md) — Detailed control table
- [powerbi-semantic-model-explained.md](powerbi-semantic-model-explained.md) — DAX and PL-300 mapping
