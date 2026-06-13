# Case Study 1: WinINET Proxy Drift (Dead Localhost Proxy)

## Executive Summary

A corporate laptop appeared online — ping and DNS worked — but browsers failed with proxy connection errors. The root issue was **stale WinINET proxy configuration** pointing at a localhost port with no active listener. This is a common endpoint reliability failure, not necessarily malware. The toolkit classified the state as `DEAD_PROXY_CONFIG`, supported the hypothesis with structured proof, and recommended a **policy-gated WinINET disable** with dry-run preview and audit logging — without claiming certainty about who wrote the registry key.

## Situation

An employee reported that Chrome and Edge could not load internal or external HTTPS sites. IT initially suspected a network outage or DNS failure. Basic connectivity checks (`ping`, `nslookup`) succeeded. The issue was isolated to WinINET-aware applications (browsers, some desktop apps).

## Symptoms

- Browser error: `ERR_PROXY_CONNECTION_FAILED` or similar proxy-related message
- `ping 8.8.8.8` succeeds
- `nslookup` resolves hostnames correctly
- Some CLI tools using WinHTTP may still work while browsers fail
- User had recently closed a development tool that may have used a local proxy

## Initial Observation

| Signal | Value | Tier |
|--------|-------|------|
| WinINET `ProxyEnable` | `1` | Observation |
| WinINET `ProxyServer` | `127.0.0.1:59081` | Observation |
| WinHTTP direct access | `true` (no proxy) | Observation |
| Listener on port 59081 | **not found** | Observation |

**Important:** Observing proxy settings in the registry does not prove who set them or whether the endpoint is compromised.

## Hypothesis

| # | Hypothesis | Likelihood |
|---|------------|------------|
| H1 | Browser failure caused by dead WinINET localhost proxy | High |
| H2 | DNS or upstream network outage | Low (contradicted by ping/DNS) |
| H3 | Active MITM on the proxy path | Unsubstantiated (no listener, no TLS anomaly) |
| H4 | Malware persistence | Requires further validation (no writer proof without telemetry) |

## Evidence Collected

### Commands (fixture-safe replay)

```powershell
pip install -e ".[dev]"
$env:PYTHONPATH = (Get-Location).Path

python -m windows_network_toolkit proxy-status --fixture tests/fixtures/enert/dead_proxy_59081.json
python -m windows_network_toolkit diagnose --proof --fixture tests/fixtures/enert/dead_proxy_59081.json
python -m windows_network_toolkit proxy-owner --fixture tests/fixtures/enert/dead_proxy_59081.json
python -m windows_network_toolkit proxy-report --fixture tests/fixtures/enert/dead_proxy_59081.json
```

### Registry values (observed)

```
HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings
  ProxyEnable = 1
  ProxyServer = 127.0.0.1:59081
```

### Listener / process info

```json
{
  "localhost_port": 59081,
  "listener_found": false,
  "process": null
}
```

### Proof envelope results

| Proof attempt | Status | Meaning |
|---------------|--------|---------|
| `localhost_listener_check` | failed | No process listening on configured port |
| `wininet_winhttp_comparison` | supported | Browser proxy path differs from WinHTTP direct path |

**Conclusion:** `supported` (confidence ~0.92)

### Timeline (drift pattern)

From `windows_network_toolkit/examples/proxy_drift_incident.jsonl`:

```
10:01:00  PROXY_ENABLE observed (ProxyEnable=1)
10:01:10  proxy_server_localhost → 127.0.0.1:56186
10:01:15  wininet_winhttp_divergent → true
10:02:00  browser_https_failed → true
10:02:05  proxy_bypass_succeeded → true
10:02:10  direct_path_success → true
```

### Classification output

```json
{
  "primary_classification": "DEAD_PROXY_CONFIG",
  "secondary_signals": ["WININET_WINHTTP_MISMATCH", "LOCALHOST_PROXY", "DEAD_LOCALHOST_PORT"],
  "confidence": 0.92,
  "limitations": ["Does not prove malware or MITM."]
}
```

## Analysis

| Hypothesis | Evidence for | Evidence against |
|------------|--------------|------------------|
| H1 Dead proxy | No listener; WinINET/WinHTTP mismatch; direct path succeeds | — |
| H2 Network outage | — | Ping/DNS OK; direct HTTPS path OK |
| H3 MITM | — | No listener; no TLS cert mismatch in this case |
| H4 Malware | Proxy drift pattern | No registry writer proof without Sysmon E13 |

The evidence **supports** H1 and **weakens** H2. H3 and H4 remain **unproven** — the toolkit surfaces this in `limitations[]`.

## Decision

**Recommended action:** Preview `DISABLE_WININET_PROXY` (HKCU registry mutation only).

**Policy gates:**

- Dry-run is default
- Typed confirmation required: `--confirm DISABLE_WININET_PROXY`
- Process kill, firewall reset, adapter disable, and WinHTTP modification are **blocked**

```powershell
# Preview (no host mutation)
python -m windows_network_toolkit proxy-disable --dry-run

# Apply only after operator review (Windows, audited)
python -m windows_network_toolkit proxy-disable --dry-run false --confirm DISABLE_WININET_PROXY
```

## Action Taken

1. Ran read-only diagnosis and proof collection
2. Reviewed dry-run remediation preview
3. Applied WinINET disable with typed confirmation (after LKG snapshot)
4. Verified browser connectivity restored
5. Started `proxy-watch` to detect reverter respawn (`REVERTER_SUSPECTED`)

## Result

- Browsers restored HTTPS connectivity
- WinINET proxy disabled; WinHTTP unchanged
- Audit event appended to `.audit/proxy-disable.jsonl`
- Incident report generated with evidence chain and limitations

## Risk Controls

The toolkit **does not**:

- Silently kill processes
- Reset firewall rules
- Disable network adapters
- Modify WinHTTP without explicit policy
- Claim malware or MITM without proof tier evidence
- Execute remediation without dry-run preview and confirmation

## Lessons Learned

| Principle | Application |
|-----------|-------------|
| **Observation ≠ Proof** | Registry shows proxy enabled — that is observation. Structured contrast checks provide proof that the proxy path fails. |
| **Correlation ≠ Causation** | A dead port correlates with browser failure; we did not assume a malicious writer without telemetry. |
| **Confidence ≠ Certainty** | 0.92 confidence is ordinal scoring, not probability of compromise. |
| **Policy Permission ≠ Safety Guarantee** | Even an allowed disable requires confirmation, rollback plan, and post-change monitoring. |

## Interview Talking Points

- Diagnosed a **WinINET vs WinHTTP split** — a pattern that breaks browsers while ping/DNS still work
- Built an **evidence chain** from registry read → listener check → path contrast → classification → policy gate
- Chose **minimal remediation** (WinINET disable) over destructive shortcuts (firewall reset, adapter bounce)
- Documented **limitations explicitly** — did not over-claim to security stakeholders
- Designed for **audit replay** — JSONL timeline suitable for incident review and IT risk workshops
- Separated **tier-1 observation** from **tier-3 proof** in client-facing language
