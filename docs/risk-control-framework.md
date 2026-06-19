# Risk Control Framework — Endpoint Proxy Technology Risk

**Status:** Normative control catalog for workshops, internal audit, and portfolio demos  
**Implementation:** `windows_network_toolkit/control_tests.py`, `src/platform_core/risk/control_test_mature.py`, `src/platform_core/governance/audit_report.py`  
**Disclaimer:** Informational mapping — not SOC 2, ISO 27001, or regulatory attestation.

---

## Framework purpose

This framework defines **control objectives**, **activities**, and **test criteria** for Windows endpoint WinINET proxy reliability and governance. Controls are designed to:

1. Detect misconfiguration before destructive remediation
2. Prevent accusatory language without writer proof
3. Gate remediation behind preview and human confirmation
4. Preserve tamper-evident audit evidence for reconstruction

**Governing principle:** Observation ≠ proof; correlation ≠ causation; classification ≠ accusation.

---

## Control objectives (formal)

| Objective ID | Statement |
|--------------|-----------|
| OBJ-REL | Maintain reliable browser HTTPS access when WinINET proxy is enabled |
| OBJ-ALIGN | WinINET and WinHTTP proxy stacks shall remain aligned per corporate policy |
| OBJ-ATTR | Proxy configuration changes shall be attributable to a known process or approved change |
| OBJ-DRIFT | Proxy drift, reverter loops, and stale configs shall be detected before remediation |
| OBJ-SAFE | Remediation shall default to preview-only with typed confirmation |
| OBJ-AUDIT | Decisions shall be recorded in append-only hash-chained audit JSONL |

---

## Control activities

| Activity | Description | Primary modules |
|----------|-------------|-----------------|
| ACT-OBSERVE | Read-only proxy state, listener, health probes | `proxy_state`, `proxy_health`, `proxy_owner` |
| ACT-WATCH | Continuous drift detection via proxy-watch | `watch.py`, `proxy_state_machine.coalesce_proxy_events` |
| ACT-CLASSIFY | Full-state transition and incident classification | `proxy_state_machine.py`, `incident_classifier.py` |
| ACT-TEST | Evaluate CTRL-001 … CTRL-010 | `control_tests.py`, `control_test_mature.py` |
| ACT-POLICY | Map risk to policy decision | `evidence_to_action.py`, policy matrix |
| ACT-PREVIEW | Generate remediation preview | `proxy_remediation.py` |
| ACT-REPORT | Governance and Power BI export | `audit_report.py`, `powerbi_star_export.py` |

---

## Control catalog — CTRL-001 through CTRL-010

### CTRL-001 — Dead WinINET Proxy Detection

| Attribute | Value |
|-----------|-------|
| **Control type** | Detective / preventive (triage) |
| **Objective** | Detect WinINET proxy pointing to localhost without a working forward path before remediation |
| **Frequency** | Per incident; continuous when proxy-watch enabled |
| **Owner** | IT Operations / Endpoint Engineering |
| **Code mapping** | `WININET_LOCALHOST_PROXY_HEALTH`, mature `CTRL-EPR-001` |
| **Evidence** | `proxy-status`, `proxy-health`, `probe_result` EvidenceEvent, health `proxy_status=DEAD_LOCALHOST_PROXY` |
| **Test procedure** | 1) Confirm WinINET localhost proxy enabled. 2) Run path probes. 3) Compare listener state. 4) Record proof tier ≥ T1 |
| **Pass criteria** | `proxy_status` in `HEALTHY_LOCALHOST_PROXY`, `BOTH_DIRECT_AND_PROXY_WORK`, or `PROXY_ONLY_WORKS`; or control NOT_TESTED when proxy disabled |
| **Fail criteria** | `DEAD_LOCALHOST_PROXY`, `DIRECT_ONLY_WORKS`, `LISTENER_NOT_PROXY`, `BOTH_DIRECT_AND_PROXY_FAIL` |
| **Partial criteria** | Health audit incomplete or ambiguous status |
| **Limitation** | Proves path failure, not why proxy was configured or who wrote registry |

---

### CTRL-002 — WinINET / WinHTTP Stack Alignment

| Attribute | Value |
|-----------|-------|
| **Control type** | Detective |
| **Objective** | Identify inconsistent proxy configuration across WinINET and WinHTTP |
| **Frequency** | Per diagnosis; quarterly sample for fleet governance |
| **Owner** | Platform Engineering / Endpoint Reliability |
| **Code mapping** | `WININET_WINHTTP_ALIGNMENT`, mature `CTRL-EPR-002` |
| **Evidence** | `wininet_proxy_enabled`, `winhttp_direct_access`, transition `WININET_WINHTTP_MISMATCH` |
| **Test procedure** | Compare WinINET enable/server with WinHTTP direct-access flag; classify mismatch |
| **Pass criteria** | Proxy disabled, or both stacks indicate aligned proxied/direct posture |
| **Fail criteria** | WinINET enabled with WinHTTP direct access |
| **Partial criteria** | WinHTTP probe unavailable on platform |
| **Limitation** | Alignment check does not prove corporate policy compliance |

---

### CTRL-003 — Localhost Proxy Path Health

| Attribute | Value |
|-----------|-------|
| **Control type** | Detective |
| **Objective** | Localhost WinINET proxy must forward external HTTPS when enabled |
| **Frequency** | Per incident involving localhost proxy |
| **Owner** | IT Support |
| **Code mapping** | `WININET_LOCALHOST_PROXY_HEALTH` (health sub-check) |
| **Evidence** | TCP listen, connect, HTTPS probe results in `probe_result` |
| **Test procedure** | Parse ProxyServer; probe direct and proxied paths; record failure_reason |
| **Pass criteria** | External HTTPS succeeds via proxy path when localhost proxy intended |
| **Fail criteria** | Enabled localhost proxy with failed proxy path and working direct path |
| **Partial criteria** | Network blocked in CI/fixture-only run |
| **Limitation** | Successful probe does not prove proxy is safe or authorized |

---

### CTRL-004 — Local Proxy Listener Governance & Attribution

| Attribute | Value |
|-----------|-------|
| **Control type** | Detective / governance |
| **Objective** | Proxy registry changes should have known, attributable owner when listener present |
| **Frequency** | Per incident with enabled proxy |
| **Owner** | Security Operations / IT Risk |
| **Code mapping** | `WININET_PROXY_OWNER_VERIFICATION`, mature `CTRL-EPR-003` |
| **Evidence** | `proxy-owner`, listener process name/PID/path, optional Sysmon E13 |
| **Test procedure** | Resolve listener on configured port; check writer proof tier |
| **Pass criteria** | T4 writer proof present, or trusted dev tool with documented exception |
| **Fail criteria** | No listener when proxy enabled toward localhost |
| **Partial criteria** | Listener found but writer proof unavailable (correlation only) |
| **Limitation** | Process on port ≠ registry writer; correlation only without E13 |

---

### CTRL-005 — PAC Configuration Observability

| Attribute | Value |
|-----------|-------|
| **Control type** | Detective |
| **Objective** | PAC URL changes are observable and subject to change management |
| **Frequency** | Per PAC-related transition |
| **Owner** | IT Governance / Change Advisory |
| **Code mapping** | mature `CTRL-EPR-004`, transition `PAC_CONFIGURED` / `PAC_REMOVED` |
| **Evidence** | `wininet_auto_config_url`, proxy-watch timeline |
| **Test procedure** | Detect PAC add/change/remove via full-state transition |
| **Pass criteria** | PAC present and logged; or NOT_TESTED when no PAC |
| **Fail criteria** | PAC changed without audit trail (operational gap — outside toolkit scope) |
| **Partial criteria** | PAC URL present but fetch/validation not run |
| **Limitation** | Toolkit observes URL string — does not validate PAC script content |

---

### CTRL-006 — Unknown Local Proxy Triage (Non-Accusatory)

| Attribute | Value |
|-----------|-------|
| **Control type** | Preventive (narrative) |
| **Objective** | Prevent malware verdict without registry writer attribution proof |
| **Frequency** | Per `UNKNOWN_LOCAL_PROXY` classification |
| **Owner** | Cyber Risk Triage |
| **Code mapping** | mature `CTRL-EPR-005`, governance human-review queue |
| **Evidence** | classification, `writer_attribution`, `limitations[]` |
| **Test procedure** | Require human review when listener exists without proven registry writer |
| **Pass criteria** | Triage completed with limitations documented; no accusatory narrative |
| **Fail criteria** | Malware/compromise language in output without T4+ writer proof |
| **Partial criteria** | Writer proof collected but intent still unknown |
| **Limitation** | Control tests narrative discipline — not EDR replacement |

---

### CTRL-007 — Proxy Reverter & Drift Detection

| Attribute | Value |
|-----------|-------|
| **Control type** | Detective |
| **Objective** | Detect proxy settings returning after disable without operator confirmation |
| **Frequency** | Continuous during proxy-watch; per remediation window |
| **Owner** | Security Operations / Endpoint Reliability |
| **Code mapping** | `PROXY_REVERTER_DETECTION`, mature `CTRL-EPR-006`, `detect_reverter_loop_pattern` |
| **Evidence** | proxy-watch JSONL, `reverter_diagnosis`, coalesced transitions |
| **Test procedure** | Review timeline for repeated enable/disable cycles on same localhost port |
| **Pass criteria** | No reverter or flapping pattern in window |
| **Fail criteria** | `REVERTER_SUSPECTED`, `PROXY_FLAPPING`, `STALE_PROXY_AFTER_PROCESS_EXIT` |
| **Partial criteria** | Pattern suggestive but window incomplete |
| **Limitation** | Correlation only — collect Sysmon E13 before process action |

---

### CTRL-008 — Direct vs Proxy Path Comparison

| Attribute | Value |
|-----------|-------|
| **Control type** | Detective |
| **Objective** | Compare direct HTTPS path with WinINET localhost proxy path |
| **Frequency** | Per health audit |
| **Owner** | IT Operations |
| **Code mapping** | `DIRECT_VS_PROXY_PATH_COMPARISON` |
| **Evidence** | `direct_probe_ok`, `proxy_probe_ok`, `proxy_status` |
| **Test procedure** | Run paired probes; record outcomes |
| **Pass criteria** | Both paths work, or failure mode documented with recommendation |
| **Fail criteria** | Direct OK, proxy fail (browser likely broken via proxy) |
| **Partial criteria** | Proxy OK, direct fail (VPN/tunnel dependency) |
| **Limitation** | Path contrast supports triage — not TLS/MITM proof alone |

---

### CTRL-009 — Policy-Gated Safe Remediation

| Attribute | Value |
|-----------|-------|
| **Control type** | Preventive |
| **Objective** | Destructive remediation remains preview-only or requires typed confirmation |
| **Frequency** | Every remediation attempt |
| **Owner** | Platform Engineering / IT Governance |
| **Code mapping** | `SAFE_REMEDIATION_POLICY`, CLI `--dry-run` default |
| **Evidence** | Policy decision JSON, audit log, dry-run output |
| **Test procedure** | Verify read-only defaults; attempt apply without confirmation → blocked |
| **Pass criteria** | Health/watch read-only; disable defaults dry-run; no auto process kill |
| **Fail criteria** | Silent registry mutation or kill without audit (regression) |
| **Partial criteria** | Operator manually runs ungated commands outside toolkit |
| **Limitation** | Documents toolkit defaults — cannot enforce operator shell actions |

---

### CTRL-010 — Audit Hash Chain & Evidence Integrity

| Attribute | Value |
|-----------|-------|
| **Control type** | Detective / ITGC |
| **Objective** | Decision audit trail is append-only and tamper-evident |
| **Frequency** | Before governance export; per audit period close |
| **Owner** | Internal Audit / Risk Advisory |
| **Code mapping** | `src/platform_core/governance/chain_of_custody.verify_chain`, `governance-report` |
| **Evidence** | `audit verify` result, `audit_chain_verification` in report |
| **Test procedure** | Replay JSONL; recompute hashes from genesis |
| **Pass criteria** | `verified: true`, zero `hash_chain_invalid_count` |
| **Fail criteria** | Chain break at any index |
| **Partial criteria** | Empty audit dir — nothing to verify |
| **Limitation** | Proves log integrity, not truth of observations or completeness |

---

## Pass / fail language guidelines (audit-safe)

### Use

- "Control **PASS** for scoped objective given evidence tier T2."
- "Control **FAIL** — direct path succeeded; proxy path failed; preview disable recommended after human review."
- "Control **PARTIAL** — listener correlated with process X; registry writer proof unavailable."
- "Control **NOT_TESTED** — WinINET localhost proxy not enabled; control not applicable."

### Avoid

- "Control passed — endpoint is secure."
- "FAIL proves malware."
- "PARTIAL means probably compromised."
- "Hash chain valid — findings are true."

### Mandatory qualifiers

Every control test output in client-facing materials must include:

1. **Evidence tier** referenced
2. **Limitations** array or footnote
3. **Scope** (single endpoint, fixture, audit period)
4. **Non-attestation** disclaimer when presenting to audit committees

---

## Mapping to incident classes

| Incident class | Primary controls exercised |
|----------------|---------------------------|
| `DEAD_PROXY_CONFIG` | CTRL-001, CTRL-003, CTRL-008, CTRL-004 |
| `WININET_WINHTTP_MISMATCH` | CTRL-002 |
| `LOCAL_PROXY_ACTIVE` | CTRL-003, CTRL-004 |
| `UNKNOWN_LOCAL_PROXY` | CTRL-004, CTRL-006 |
| `PAC_CONFIGURED` | CTRL-005 |
| `REVERTER_SUSPECTED` | CTRL-007, CTRL-009 |
| `POSSIBLE_MITM_RISK` | CTRL-008 (+ TLS proof outside this catalog) |

See [control-matrix.md](control-matrix.md) for the consolidated table.

---

## Related documents

- [control-testing-methodology.md](control-testing-methodology.md)
- [audit-evidence-model.md](audit-evidence-model.md)
- [evidence_to_action_governance_model.md](evidence_to_action_governance_model.md)
