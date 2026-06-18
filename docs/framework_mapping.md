# Cyber Risk Framework Mapping

Maps platform capabilities to **NIST CSF 2.0**, **ISO 27001-style** themes, and **MITRE ATT&CK** (triage context only).

**Disclaimer:** Partial support is marked **partial**. This is decision infrastructure — not SOC 2 attestation, SIEM, or EDR.

See also: [control-matrix.md](control-matrix.md) · [evidence_to_action_governance_model.md](evidence_to_action_governance_model.md)

---

## NIST CSF 2.0

| Function | Control objective | Evidence from this repo | Test procedure | Pass / Fail / Exception | Limitations | Owner | Audit artifact |
|----------|-------------------|-------------------------|--------------|-------------------------|-------------|-------|----------------|
| **Govern** | Risk decisions documented with limitations | `governance-report`, `risk-assess`, governance envelope | Run `governance-report --audit-dir` | Pass if limitations[] present | Not regulatory attestation | IT Governance | `reports/`, CLI JSON |
| **Identify** | Asset and threat context for incidents | `risk-assess` asset/threat models | `risk-assess --fixture` | Pass if asset + threat populated | Fixture-scoped | IT Risk | case study JSON |
| **Protect** | Remediation gated; no silent destructive action | `proxy-disable --dry-run`, policy engine | `test_policy_safety_contract.py` | Fail if execute without confirmation | partial — endpoint agent separate | Platform Engineering | audit JSONL |
| **Detect** | Proxy/TLS drift detection | `proxy-status`, `diagnose --proof` | `control-test`, CT_PROXY_DRIFT | Pass on drift signal | Observation ≠ proof | IT Operations | `.audit/*.jsonl` |
| **Respond** | Preview-only remediation default | policy `PREVIEW_ONLY` | CT_REMEDIATION_SAFETY | Pass if dry_run default | Recommendation ≠ execution authority | IT Operations | remediation_actions.csv |
| **Recover** | Rollback plan + verification hooks | `proxy-disable` snapshots | Manual review of rollback_plan | partial — not auto-rollback | Human approval required | IT Operations | proxy-disable.jsonl |

---

## ISO 27001-style (selected)

| Theme | Control objective | Evidence | Test | Criteria | Limitations | Owner | Artifact |
|-------|-------------------|----------|------|----------|-------------|-------|----------|
| A.8 Asset management | WinINET config as critical asset | `asset_for_fixture()` | risk-assess | Pass if asset typed | partial | IT Ops | risk-assess JSON |
| A.12 Operations security | Change management for proxy | audit trail + preview | CT-AUDIT-001 | Pass if audit exists | partial | Internal Audit | audit JSONL |
| A.16 Incident management | Evidence-backed triage | proof envelope | diagnose --proof | Pass if conclusion + limitations | Not malware verdict | Security | incident timeline |
| A.18 Compliance | Ordinal risk scoring documented | risk KPI, business impact | `risk-kpi-summary` | Pass if confidence_type ordinal | Not probability | GRC | risk_kpi JSON |

---

## MITRE ATT&CK (triage context only — not accusation)

| Technique context | Platform signal | Classification | Limitation |
|-------------------|-----------------|----------------|------------|
| T1557 Adversary-in-the-Middle (context) | TLS path mismatch | `POSSIBLE_MITM_RISK` | **Not confirmed MITM** — triage only |
| T1090 Proxy (context) | Unknown localhost listener | `UNKNOWN_LOCAL_PROXY` | **Not malware proof** |
| T1112 Modify Registry (context) | Writer attribution tier | `CORRELATED` / `PROVEN_REGISTRY_WRITER` | Correlation ≠ causation without network proof |

**Rule:** MITRE labels support **review vocabulary** only. `classification_is_accusation: false` in governance outputs.

---

## Control test cross-reference

Formal engine: `src/platform_core/controls/control_test.py` · Docs: [control_test_engine.md](control_test_engine.md)
