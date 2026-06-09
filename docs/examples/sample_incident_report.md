# Endpoint Reliability Incident Report (Sample)

> Synthetic fixture output — not a real incident. Observation ≠ proof.

## 1. Executive Summary

Based on collected evidence, the endpoint exhibited WinINET proxy drift symptoms. Browser path failed through loopback proxy while direct path succeeded. Recommended: preview-only remediation after typed confirmation.

## 2. Incident Timeline

See `windows_network_toolkit/examples/proxy_drift_incident.jsonl`

## 3. Evidence Table

| Signal | Value | Tier |
|--------|-------|------|
| wininet_proxy_enabled | true | CORRELATED |
| proxy_bypass_succeeded | true | PROVEN_NETWORK_IMPACT |

## 4. Hypothesis

WININET proxy drift — direct path succeeds, proxy path fails.

## 5. Policy Gate

`PREVIEW_ONLY` — no execute without confirmation.

## 6. Residual Risk

Policy permission is not a safety guarantee.

Generate live: `make demo`
