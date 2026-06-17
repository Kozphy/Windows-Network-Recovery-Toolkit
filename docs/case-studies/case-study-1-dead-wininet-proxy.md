# Case Study 1 — Dead WinINET Localhost Proxy

## Business Problem

Employees cannot access SaaS, SSO, or internal web applications while basic connectivity tests still pass. IT support tickets are misrouted as network outages. Manual registry fixes create **unaudited changes** and compliance exposure.

## Technical Symptom

- Ping and DNS succeed
- Browsers and WinINET-aware apps fail on HTTPS
- WinHTTP-based tools may still work
- WinINET shows `ProxyEnable=1`, `ProxyServer=127.0.0.1:59081`
- No listener on port 59081

## Evidence Collected

| Signal | Value | Tier |
|--------|-------|------|
| WinINET proxy enabled | true | Observation |
| ProxyServer | 127.0.0.1:59081 | Observation |
| WinHTTP | direct | Observation |
| Listener on 59081 | false | Observation |
| WinINET/WinHTTP contrast | divergent | Proof (supported) |

Fixture: `tests/fixtures/enert/dead_proxy_59081.json`

```powershell
python -m windows_network_toolkit proxy-status --fixture tests/fixtures/enert/dead_proxy_59081.json
python -m windows_network_toolkit diagnose --proof --fixture tests/fixtures/enert/dead_proxy_59081.json
```

## Classification

**Primary:** `DEAD_PROXY_CONFIG`  
**Secondary:** `WININET_WINHTTP_MISMATCH`, `LOCALHOST_PROXY`, `DEAD_LOCALHOST_PORT`  
**Severity:** medium · **Confidence:** 0.92 (ordinal)

## Proof Level

Structured proof **supported** via localhost listener check and WinINET/WinHTTP comparison.  
Does **not** prove malware, MITM, or registry writer identity.

## Risk Assessment

| Dimension | Rating |
|-----------|--------|
| Inherent risk | Medium (productivity impact) |
| Residual risk | Medium–Low after controls |
| Security escalation | Not warranted without additional telemetry |

## Policy Decision

**Outcome:** `PREVIEW_ONLY`  
**Action allowed:** `DISABLE_WININET_PROXY` only with typed confirmation and rollback review.

## Remediation Preview

```powershell
python -m windows_network_toolkit proxy-disable --dry-run
```

Default dry-run — no registry mutation. Apply only after explicit approval.

## Limitations

- Does not prove malware or unauthorized persistence
- Does not identify registry writer without Sysmon E13 or equivalent
- Confidence is ordinal, not a statistical probability
- Policy permission is not a safety guarantee

## Audit Trail

Append-only JSONL with hash-chain verification (`audit verify`). Case fixture: `tests/fixtures/case_studies/case_1_dead_wininet_proxy.json`

## Interview Explanation

> "This is a **reliability** incident with **proof-supported** classification, not a security verdict. I built a workflow that separates observation from proof, rates risk honestly, and keeps remediation preview-only until governance requirements are met — the same pattern IT Risk and Internal Audit expect for control testing."

**Related:** [dead-localhost-proxy.md](dead-localhost-proxy.md) · [technology_risk_control_matrix.md](../technology_risk_control_matrix.md)
