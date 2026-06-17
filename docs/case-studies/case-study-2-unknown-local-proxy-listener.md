# Case Study 2 — Unknown Local Proxy Listener

## Business Problem

Security and IT teams must triage localhost proxy listeners without falsely accusing users of compromise or killing unknown processes without evidence. Listener presence alone is insufficient for escalation.

## Technical Symptom

- WinINET proxy enabled toward `127.0.0.1:61526`
- Active listener on configured port
- Process name not on known-dev or security-tool allowlist
- Registry writer **not** confirmed in initial scope

## Evidence Collected

| Signal | Value | Tier |
|--------|-------|------|
| ProxyServer | 127.0.0.1:61526 | Observation |
| Listener PID | 9999 | Observation |
| Process | unknown_svc.exe | Correlation |
| Registry writer | not identified | Not proven |

Fixture: `tests/fixtures/enert/unknown_localhost_proxy.json`

```powershell
python -m windows_network_toolkit proxy-writer-attribution --fixture unknown_localhost_proxy.json
python -m windows_network_toolkit proxy-owner --fixture unknown_localhost_proxy.json
```

## Classification

**Primary:** `UNKNOWN_LOCAL_PROXY`  
**Confidence:** ~0.35 (low — ordinal)

## Proof Level

**Observation / correlation only.** Listener match ≠ registry writer. No final causation claimed.

## Risk Assessment

| Dimension | Rating |
|-----------|--------|
| Inherent risk | Medium–High (investigation required) |
| Residual risk | High until writer attribution or software inventory |
| Auto-remediation | Not appropriate |

## Policy Decision

**Outcome:** `REQUIRE_TYPED_CONFIRMATION` for any allowlisted change.  
**Blocked:** `KILL_PROXY_PROCESS`, firewall reset, adapter disable (by default).

## Remediation Preview

Investigate first — software inventory, parent process tree, optional Sysmon E13.  
No silent process termination.

## Limitations

- Listener ≠ registry writer
- Does not prove malware
- Heuristic risk scores are not blocking verdicts
- Correlation must not be treated as causation

## Audit Trail

Document observations, attribution attempts, and escalation decisions in append-only JSONL. Do not destroy evidence via aggressive cleanup scripts.

## Interview Explanation

> "This case shows why the platform separates **listener attribution** from **registry writer proof**. I'd present it to cyber risk stakeholders as a control-testing scenario: detective controls fired, but preventive response stays gated until evidence tier improves."

**Related:** [case-study-2-unknown-local-proxy-listener.md](../case-study-2-unknown-local-proxy-listener.md)
