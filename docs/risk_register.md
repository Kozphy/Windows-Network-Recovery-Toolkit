# Risk Register — Technology Risk Portfolio

Ordinal risk register for demonstrations. **Not** a production GRC export or formal risk acceptance record.

**Fixture:** `tests/fixtures/risk_register/sample_risk_register.json`

---

## Register (summary)

| Risk ID | Title | Likelihood (1–5) | Impact (1–5) | Inherent | Residual | Controls | Limitation |
|---------|-------|------------------|--------------|----------|----------|----------|------------|
| RISK-001 | Dead WinINET localhost proxy | 4 | 3 | Medium | Medium | CTRL-001, CTRL-008, CTRL-009 | Reliability — not malware |
| RISK-002 | Unknown listener without writer proof | 3 | 3 | Medium | Medium | CTRL-004, CTRL-006 | Correlation ≠ registry writer |
| RISK-003 | TLS path mismatch (triage) | 2 | 4 | High | High | CTRL-008, path proof | Not confirmed MITM |

**Likelihood and impact are ordinal ranks — not probabilities.**

---

## RISK-001 — Dead WinINET localhost proxy

| Field | Value |
|-------|-------|
| Asset | WinINET proxy / browser egress |
| Scenario | ProxyServer points to localhost with no listener |
| Evidence | `proxy-status`, `diagnose --proof`, audit JSONL |
| Controls | CTRL-001, CTRL-008, CTRL-009 |
| Owner | IT Operations |
| Action | Preview `proxy-disable` with typed confirmation |
| Status | Open |

---

## RISK-002 — Unknown localhost listener

| Field | Value |
|-------|-------|
| Asset | Process attribution / proxy path |
| Scenario | Listener on port; registry writer unknown without Sysmon |
| Evidence | `proxy-owner`, writer attribution tier |
| Controls | CTRL-004, CTRL-006 |
| Owner | Security / IT Risk |
| Action | Collect E13; human review — no malware narrative |
| Status | Open |

---

## RISK-003 — TLS path mismatch (triage)

| Field | Value |
|-------|-------|
| Asset | HTTPS certificate path |
| Scenario | Proxied vs direct TLS chain differs |
| Evidence | `tls-proof`, path contrast |
| Controls | CTRL-008 |
| Owner | Cyber Risk / GRC |
| Action | Investigate with proof tier — not confirmed interception |
| Status | Open |

---

## Usage

```powershell
python -m windows_network_toolkit governance-report --audit-dir tests/fixtures/risk_analytics/audit_sample --format markdown
```

Embedded in governance report when sample fixture is present.

**Related:** [risk-control-framework.md](risk-control-framework.md) · [control-matrix.md](control-matrix.md)
