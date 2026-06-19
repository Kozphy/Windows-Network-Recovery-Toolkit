# Control Matrix — Technology Risk & Control Analytics

Portfolio-friendly control mapping for Big 4, Internal Audit, Cyber Risk, and FinTech operational resilience workshops.

**Full framework:** [risk-control-framework.md](risk-control-framework.md)  
**Test methodology:** [control-testing-methodology.md](control-testing-methodology.md)  
**Disclaimer:** Informational — not a formal SOC 2 or regulatory attestation. Observation ≠ proof.

---

## Summary table (business view)

| Business Objective | Asset | Threat | Control | Test | Finding | Risk | Owner |
|--------------------|-------|--------|---------|------|---------|------|-------|
| Browser access reliability | WinINET proxy config | Dead localhost proxy | Drift detection | `proxy-status`, `diagnose --proof` | `DEAD_PROXY_CONFIG` | Medium | IT Operations |
| Authorized changes | Registry proxy settings | Unknown writer | Writer attribution | Sysmon E13 correlation | `CORRELATED` / writer proof | Medium–High | Security / IT Risk |
| HTTPS trust | Certificate path | TLS mismatch | Direct vs proxied contrast | `tls-proof` | `POSSIBLE_MITM_RISK` | High if proof-supported | Security / GRC |
| Safe remediation | Endpoint config | Aggressive scripts | Policy-gated preview | `proxy-disable --dry-run` | `PREVIEW_ONLY` | Medium | Platform / IT Governance |
| Auditability | Evidence trail | Non-replayable logs | Hash-chained JSONL | `audit verify`, `governance-report` | Chain valid/invalid | Medium | Internal Audit |

---

## Detailed control matrix — CTRL-001 through CTRL-010

| ID | Control name | Control type | Frequency | Owner | Evidence sources | Test procedure | Pass criteria | Fail criteria | Limitation |
|----|--------------|--------------|-----------|-------|------------------|----------------|---------------|---------------|------------|
| **CTRL-001** | Dead WinINET Proxy Detection | Detective | Per incident; continuous with proxy-watch | IT Operations / Endpoint Engineering | `proxy-status`, `proxy-health`, `probe_result` EvidenceEvent, `proxy_status` | Confirm localhost proxy enabled → run path/listener checks → record tier ≥ T1 | Healthy proxy path, or NOT_TESTED when proxy disabled | `DEAD_LOCALHOST_PROXY`, `DIRECT_ONLY_WORKS`, listener not proxy | Proves path failure — not why configured or who wrote registry |
| **CTRL-002** | WinINET / WinHTTP Stack Alignment | Detective | Per diagnosis; quarterly sample | Platform Engineering | `wininet_proxy_enabled`, `winhttp_direct_access`, transition class | Compare WinINET enable/server vs WinHTTP direct flag | Stacks aligned or proxy disabled | WinINET enabled + WinHTTP direct access | Alignment ≠ corporate policy compliance |
| **CTRL-003** | Localhost Proxy Path Health | Detective | Per localhost proxy incident | IT Support | TCP listen/connect, HTTPS probe in `probe_result` | Parse ProxyServer → probe external HTTPS via proxy path | Proxy path succeeds when intended | Enabled localhost proxy with failed proxy path | Successful probe ≠ safe or authorized proxy |
| **CTRL-004** | Local Proxy Listener Governance & Attribution | Detective / Governance | Per enabled proxy incident | Security Operations / IT Risk | `proxy-owner`, process metadata, optional Sysmon E13 | Resolve listener; check writer proof tier | T4 writer proof or documented dev exception | No listener when proxy enabled toward localhost | Process on port ≠ registry writer without E13 |
| **CTRL-005** | PAC Configuration Observability | Detective | Per PAC transition | IT Governance / Change Advisory | `wininet_auto_config_url`, proxy-watch timeline | Detect PAC add/change/remove via full-state transition | PAC observed and logged; or NOT_TESTED | PAC changed without audit trail (org process gap) | Observes URL — does not validate PAC script |
| **CTRL-006** | Unknown Local Proxy Triage (Non-Accusatory) | Preventive (narrative) | Per `UNKNOWN_LOCAL_PROXY` | Cyber Risk Triage | classification, `writer_attribution`, `limitations[]` | Human review; block accusatory language without T4+ | Triage with limitations; no malware verdict | Malware/compromise language without writer proof | Narrative control — not EDR |
| **CTRL-007** | Proxy Reverter & Drift Detection | Detective | Continuous during proxy-watch | Security Ops / Endpoint Reliability | proxy-watch JSONL, `reverter_diagnosis`, coalesced transitions | Timeline review for enable/disable cycles on same port | No reverter/flapping in window | `REVERTER_SUSPECTED`, `PROXY_FLAPPING`, stale proxy | Correlation only — collect E13 before process action |
| **CTRL-008** | Direct vs Proxy Path Comparison | Detective | Per health audit | IT Operations | `direct_probe_ok`, `proxy_probe_ok`, `proxy_status` | Paired HTTPS/TCP probes | Both paths OK or documented failure mode | Direct OK + proxy fail | Path contrast — not standalone MITM proof |
| **CTRL-009** | Policy-Gated Safe Remediation | Preventive | Every remediation attempt | Platform Engineering / IT Governance | Policy JSON, audit log, `--dry-run` output | Verify read-only defaults; apply without confirmation blocked | Health/watch read-only; disable dry-run default | Silent mutation or auto kill (regression) | Toolkit defaults only — not operator shell enforcement |
| **CTRL-010** | Audit Hash Chain & Evidence Integrity | Detective / ITGC | Before export; period close | Internal Audit / Risk Advisory | `audit verify`, `audit_chain_verification` | Replay JSONL; recompute hashes from genesis | `verified: true` | Chain break at any index | Integrity ≠ truth of observations |

### Control objectives (CTRL-001–010)

| ID | Objective |
|----|-----------|
| CTRL-001 | Detect dead localhost WinINET proxy paths before ad-hoc registry resets |
| CTRL-002 | Surface WinINET/WinHTTP stack misalignment that breaks predictable egress |
| CTRL-003 | Validate functional health of localhost proxy listener and HTTPS path |
| CTRL-004 | Attribute localhost listeners and block writer claims without proof tier |
| CTRL-005 | Observe PAC URL changes for change-management and audit trail gaps |
| CTRL-006 | Enforce non-accusatory triage for unknown local proxy incidents |
| CTRL-007 | Detect proxy reverter/flapping patterns indicative of automation loops |
| CTRL-008 | Compare direct vs proxied paths to isolate dead-proxy vs TLS triage signals |
| CTRL-009 | Verify remediation defaults to preview and blocks silent destructive actions |
| CTRL-010 | Prove append-only audit integrity before committee or export consumption |

### Failure interpretation (CTRL-001–010)

| ID | If control FAILS | Reviewer interpretation |
|----|------------------|-------------------------|
| CTRL-001 | Dead localhost proxy path | Endpoint reliability risk — browser egress likely broken; not malware |
| CTRL-002 | WinINET/WinHTTP mismatch | Stack inconsistency — investigate config drift; not compromise proof |
| CTRL-003 | Proxy path probe failed | Functional proxy failure — verify listener and dev tooling |
| CTRL-004 | No listener / no writer proof | Correlation insufficient — collect Sysmon E13 before process action |
| CTRL-005 | PAC change without audit trail | Change management gap — not PAC script safety verdict |
| CTRL-006 | Accusatory language without proof | Narrative control breach — require human review rewrite |
| CTRL-007 | Reverter/flapping detected | Possible automation loop — correlation only; no registry writer claim |
| CTRL-008 | Direct OK, proxy fail | Classic dead-proxy symptom — prioritize reliability remediation preview |
| CTRL-009 | Silent mutation detected in tests | **Critical regression** — policy gate broken; block release |
| CTRL-010 | Hash chain invalid | Evidence integrity failure — do not use for committee reporting until fixed |

---

## Code mapping reference

| CTRL ID | Endpoint `control_tests.py` | Mature `control_test_mature.py` |
|---------|------------------------------|--------------------------------|
| CTRL-001 | `WININET_LOCALHOST_PROXY_HEALTH` | `CTRL-EPR-001` |
| CTRL-002 | `WININET_WINHTTP_ALIGNMENT` | `CTRL-EPR-002` |
| CTRL-003 | (health sub-check of CTRL-001) | — |
| CTRL-004 | `WININET_PROXY_OWNER_VERIFICATION` | `CTRL-EPR-003` |
| CTRL-005 | — | `CTRL-EPR-004` |
| CTRL-006 | — | `CTRL-EPR-005` |
| CTRL-007 | `PROXY_REVERTER_DETECTION` | `CTRL-EPR-006` |
| CTRL-008 | `DIRECT_VS_PROXY_PATH_COMPARISON` | — |
| CTRL-009 | `SAFE_REMEDIATION_POLICY` | — |
| CTRL-010 | — (platform `verify_chain`) | — |

---

## Analytics commands

```powershell
python -m windows_network_toolkit analytics-summary --audit-dir tests/fixtures/risk_analytics/audit_sample --format markdown
python -m windows_network_toolkit risk-kpi-summary --audit-dir tests/fixtures/risk_analytics/audit_sample --format markdown
python -m windows_network_toolkit governance-report --audit-dir tests/fixtures/risk_analytics/audit_sample --format markdown
python -m windows_network_toolkit risk-assess --fixture tests/fixtures/case_studies/case_1_dead_wininet_proxy.json
python -m windows_network_toolkit control-test --fixture tests/fixtures/case_studies/case_1_dead_wininet_proxy.json
python -m windows_network_toolkit powerbi-export --audit-dir tests/fixtures/risk_analytics/audit_sample --out-dir examples/powerbi/export
```

**Framework:** [framework_mapping.md](framework_mapping.md) · **SQL KPIs:** [sql_kpi_examples.md](sql_kpi_examples.md) · **Warehouse:** [analytics_data_model.md](analytics_data_model.md) · **Domain model:** [domain-model.md](domain-model.md)
