# Case 2: Proxy Reverter (Node Listener)

## Symptom

Proxy disable preview succeeds but settings revert within minutes; listener respawns on localhost port.

## Observation

| Signal | Value | Tier |
|--------|-------|------|
| `ProxyServer` | `127.0.0.1:61526` | OBSERVED_ONLY |
| Listener | present (`node.exe`) | CORRELATED |
| Registry writer proof | unavailable | missing |
| Re-enable after disable | observed | CORRELATED |

## Hypothesis

Active localhost proxy process or scheduled task re-applies WinINET keys — **correlation**, not proven writer identity.

## Evidence

- Timeline: disable preview → proxy re-enabled → listener respawn
- Process name on port (e.g. `node.exe`) — not allowlisted dev proxy

## Proof level

**Correlation** (ordinal ~0.55) — stickiness failure pattern; no Sysmon E13 in initial bundle.

## Policy decision

**OBSERVE** — collect writer telemetry; **no automatic process kill**.

## Remediation preview

Blocked repeat execute until reverter identified — `REMEDIATION_NOT_STICKY`.

## Limitations

- Listener match ≠ registry writer
- Process name alone ≠ malicious intent
- Confidence is ordinal, not certainty

## Audit trail

`event_id=evt-case2-reverter`, `source=proxy-watch`, `evidence_tier=CORRELATED`, `policy_decision=OBSERVE`

## Interview explanation

> "When remediation doesn't stick, I stop repeating disable and shift to observe — monitor reverter, collect Sysmon E13, never silently kill processes."

## Demo commands

```powershell
python -m windows_network_toolkit proxy-owner --fixture tests/fixtures/case_studies/case_2_proxy_reverter_node.json
python -m windows_network_toolkit proxy-watch --fixture tests/fixtures/case_studies/case_2_proxy_reverter_node.json
python -m windows_network_toolkit proxy-disable --dry-run
curl http://127.0.0.1:8000/platform/demo/case-studies
```
