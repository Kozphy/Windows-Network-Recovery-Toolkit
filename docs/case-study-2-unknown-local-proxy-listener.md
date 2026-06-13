# Case Study 2: Unknown Local Proxy Listener

## Executive Summary

WinINET was configured to use `127.0.0.1:61526`, and a process **was** listening on that port — but the process (`unknown_svc.exe`) was not on any known-dev or security-tool allowlist. This pattern **indicates** a localhost proxy listener that requires investigation. The toolkit classified it as `UNKNOWN_LOCAL_PROXY` with **low attribution confidence** because registry-writer proof was unavailable. No automatic process termination was performed.

## Situation

During a security triage review, an analyst noticed WinINET proxy settings pointing at a high ephemeral localhost port. Unlike the dead-proxy case, `netstat` showed an active listener. The owning process name was unfamiliar to the endpoint team.

## Symptoms

- Browser traffic routed through `127.0.0.1:61526`
- Listener present on configured port
- Process name not matching known development proxies (e.g., Cursor, Fiddler) or approved security tools
- No Sysmon Event ID 13 telemetry loaded in the initial review

## Initial Observation

| Signal | Value | Tier |
|--------|-------|------|
| `ProxyEnable` | `1` | Observation |
| `ProxyServer` | `127.0.0.1:61526` | Observation |
| Listener PID | `9999` | Observation |
| Process name | `unknown_svc.exe` | Observation (correlation) |
| Registry writer confirmed | `false` | Not proven |

**Critical distinction:** Finding a process on the proxy port is **correlation**, not proof that the process wrote the registry key.

## Hypothesis

| # | Hypothesis | Likelihood |
|---|------------|------------|
| H1 | Leftover or unapproved local proxy service | Medium |
| H2 | Legitimate dev tool using non-standard binary name | Medium |
| H3 | Suspicious or unauthorized interception | Possible — requires further validation |
| H4 | Confirmed registry writer = listener process | Unproven without Sysmon E13 |

## Evidence Collected

### Commands

```powershell
pip install -e ".[dev]"
$env:PYTHONPATH = (Get-Location).Path

python -m windows_network_toolkit proxy-writer-attribution --fixture tests/fixtures/enert/unknown_localhost_proxy.json
python -m windows_network_toolkit proxy-owner --fixture tests/fixtures/enert/unknown_localhost_proxy.json
python -m windows_network_toolkit proxy-status --fixture tests/fixtures/enert/unknown_localhost_proxy.json
```

### Registry values

```
ProxyEnable = 1
ProxyServer = 127.0.0.1:61526
```

### Listener / process info

```json
{
  "listener": {
    "pid": 9999,
    "process_name": "unknown_svc.exe"
  },
  "registry_writer_confirmed": false,
  "attribution_confidence": "low",
  "confidence_score": 0.35
}
```

### Writer attribution output

```json
{
  "classification": "UNKNOWN_LOCAL_PROXY",
  "rationale": "Proxy enabled with unclassified localhost listener.",
  "writer_evidence": [],
  "telemetry_sources": ["wininet_registry"],
  "limitations": []
}
```

### Contrast: when writer proof *is* available

Fixture `tests/fixtures/enert/registry_writer_observed.json` shows the upgrade path when Sysmon E13 is present:

```
Event ID 13 → mitmproxy.exe wrote ProxyEnable
Listener PID 5512 → mitmproxy.exe (correlation + writer proof)
Classification → SUSPICIOUS_PROXY (not automatic containment)
```

### Netstat-style evidence (representative)

```
TCP    127.0.0.1:61526    0.0.0.0:0    LISTENING    9999
```

## Analysis

| Hypothesis | Evidence for | Evidence against |
|------------|--------------|------------------|
| H1 Unapproved proxy | Unknown process name; localhost binding | Could be renamed legitimate tool |
| H2 Legitimate dev tool | Localhost-only binding | Not on known-dev allowlist |
| H3 Suspicious interception | Proxy enabled + unknown listener | No TLS mismatch or writer proof in this fixture |
| H4 Writer = listener | — | `registry_writer_confirmed: false` |

The toolkit correctly keeps confidence at **0.35** and recommends **investigation**, not autonomous kill.

**Blocked by policy:**

- `KILL_PROXY_PROCESS` — blocked
- `STOP_LISTENER_WITH_CONFIRMATION` — preview only; requires human review at low confidence

## Decision

**Recommended action:** `INVESTIGATE_LISTENER` — collect writer proof, hash, parent process tree, and software inventory before any state change.

**Next steps (manual, not automated):**

1. Collect Sysmon E13 or Procmon registry write events
2. Run `proxy-writer-attribution` with live telemetry
3. Compare executable hash against asset inventory
4. If approved security tool → reclassify to `KNOWN_SECURITY_TOOL`
5. If confirmed unauthorized → escalate to security operations with evidence bundle

## Action Taken

1. Documented listener attribution (PID, process name, port)
2. Exported incident report with `UNKNOWN_LOCAL_PROXY` classification
3. Escalated to security review with explicit "writer not confirmed" limitation
4. Did **not** kill process or modify registry automatically
5. Scheduled `proxy-watch` to detect configuration drift or reverter behavior

## Result

- Risk properly categorized as **investigate**, not **remediate**
- Security team received evidence bundle with limitations surfaced
- No unsafe automated containment
- When Sysmon data was later loaded (separate scenario), classification could upgrade with proof — not assumption

## Risk Controls

| Control | Behavior |
|---------|----------|
| No silent process kill | `KILL_PROXY_PROCESS` in blocked actions registry |
| Correlation capped | Listener match cannot unlock `FINAL_CAUSATION` without writer proof |
| Low confidence blocks aggressive remediation | Policy engine returns `PREVIEW_ONLY` or `BLOCK` |
| Limitations in output | Every classification includes what we cannot prove |

## Lessons Learned

| Principle | Application |
|-----------|-------------|
| **Observation ≠ Proof** | We observed a listener; we did not prove it wrote the proxy registry keys. |
| **Correlation ≠ Causation** | PID on port 61526 correlates with proxy traffic; it may not be the registry writer. |
| **Confidence ≠ Certainty** | 0.35 confidence means "investigate" — not "confirmed threat." |
| **Policy Permission ≠ Safety Guarantee** | Even if stop-listener were allowed, operator confirmation and rollback remain required. |

## Interview Talking Points

- Handled the **listener ≠ writer** trap — a common false attribution in proxy triage
- Used **tiered evidence** to avoid over-escalating unknown localhost proxies
- Demonstrated **policy-blocked destructive actions** when confidence is low
- Showed how **telemetry upgrades** evidence (Sysmon E13) without changing core safety model
- Explained trade-off between **speed** (kill unknown process) and **auditability** (evidence first)
- Positioned tool for **security analyst** and **IT risk** audiences — observability, not autonomous EDR
