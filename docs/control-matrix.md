# Control Matrix — Technology Risk & Control Analytics

Portfolio-friendly control mapping for Big 4, Internal Audit, Cyber Risk, and FinTech operational resilience workshops.

**Full matrix:** [technology_risk_control_matrix.md](technology_risk_control_matrix.md)

**Disclaimer:** Informational — not a formal SOC 2 or regulatory attestation. Observation ≠ proof.

---

## Summary table

| Business Objective | Asset | Threat | Control | Test | Finding | Risk | Owner |
|--------------------|-------|--------|---------|------|---------|------|-------|
| Browser access reliability | WinINET proxy config | Dead localhost proxy | Drift detection | `proxy-status`, `diagnose --proof` | `DEAD_PROXY_CONFIG` | Medium | IT Operations |
| Authorized changes | Registry proxy settings | Unknown writer | Writer attribution | Sysmon E13 correlation | `CORRELATED` / `PROVEN_REGISTRY_WRITER` | Medium–High | Security / IT Risk |
| HTTPS trust | Certificate path | TLS mismatch | Direct vs proxied contrast | `tls-proof` | `POSSIBLE_MITM_RISK` | High if proof-supported | Security / GRC |
| Safe remediation | Endpoint config | Aggressive scripts | Policy-gated preview | `proxy-disable --dry-run` | `PREVIEW_ONLY` | Medium | Platform / IT Governance |
| Auditability | Evidence trail | Non-replayable logs | Hash-chained JSONL | `audit verify`, `analytics-summary` | Chain valid/invalid | Medium | Internal Audit |

---

## Analytics commands

```powershell
python -m windows_network_toolkit analytics-summary --audit-dir tests/fixtures/risk_analytics/audit_sample --format markdown
python -m windows_network_toolkit risk-kpi-summary --audit-dir tests/fixtures/risk_analytics/audit_sample --format markdown
python -m windows_network_toolkit governance-report --audit-dir tests/fixtures/risk_analytics/audit_sample --format markdown
python -m windows_network_toolkit risk-assess --fixture tests/fixtures/case_studies/case_1_dead_wininet_proxy.json
python -m windows_network_toolkit control-test --fixture tests/fixtures/case_studies/case_1_dead_wininet_proxy.json
```

**Framework:** [framework_mapping.md](framework_mapping.md) · **SQL KPIs:** [sql_kpi_examples.md](sql_kpi_examples.md) · **Warehouse:** [analytics_data_model.md](analytics_data_model.md)
