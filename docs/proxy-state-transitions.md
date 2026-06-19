# Proxy state transitions (audit-grade)

WinINET proxy-watch uses a **state transition engine** — not single-field diffs — to classify registry observations. Observation is not proof; correlation is not causation.

## Transition classification table

| Transition class | Typical before → after | Risk | Proof tier | Policy |
| --- | --- | --- | --- | --- |
| `NO_CHANGE` | Identical core state | INFO | T0 | OBSERVE |
| `PROXY_DISABLED` | ProxyEnable 1→0, server unchanged | LOW | T1 | OBSERVE |
| `PROXY_SERVER_REMOVED` | Server cleared, proxy disabled | LOW | T1 | OBSERVE |
| `PROXY_SERVER_REMOVED_PARTIAL` | Server cleared, ProxyEnable still 1 | LOW | T1 | OBSERVE |
| `PROXY_DISABLED_AND_SERVER_REMOVED` | Server cleared + ProxyEnable 0 | LOW | T1 | OBSERVE |
| `LOCALHOST_PROXY_ENABLED` | Off → on with 127.0.0.1/localhost server | MEDIUM | T1–T2 | ALERT |
| `REMOTE_OR_NON_LOOPBACK_PROXY_CONFIGURED` | Non-empty remote ProxyServer while enabled | HIGH | T1 | REQUIRE_HUMAN_REVIEW |
| `PROXY_ENABLED_WITH_NO_SERVER` | ProxyEnable 1, empty ProxyServer | MEDIUM | T1 | ALERT |
| `PAC_CONFIGURED` | AutoConfigURL added/changed | MEDIUM | T1 | ALERT |
| `AUTODETECT_ENABLED` | AutoDetect enabled | LOW | T1 | OBSERVE |
| `WININET_WINHTTP_MISMATCH` | WinINET proxy on + WinHTTP direct | MEDIUM | T1 | ALERT |
| `LOCALHOST_PROXY_PORT_CHANGED` | Same localhost mode, different port | MEDIUM | T1 | ALERT |
| `REVERTER_SUSPECTED_LOCALHOST_PROXY_LOOP` | ≥3 enable/disable cycles, same port (5 min) | HIGH/MEDIUM | T2 | REQUIRE_HUMAN_REVIEW |
| `ERROR_INSUFFICIENT_DATA` | Incomplete snapshots | LOW | T1 | OBSERVE |

**Hard rule:** If `after.ProxyServer` is null, empty, or deleted, never classify as `REMOTE_OR_NON_LOOPBACK_PROXY_CONFIGURED`, `REMOTE_PROXY_CONFIGURED`, or `PROXY_SERVER_CHANGED_TO_REMOTE`.

## Primary classification (interview-grade)

| Primary | Meaning |
| --- | --- |
| `LOCALHOST_PROXY_REMOVED` | Loopback ProxyServer cleared |
| `PROXY_REMOVED` | Non-loopback or generic server cleared |
| `PROXY_DISABLED_OR_REMOVED` | ProxyEnable off and/or server cleared |
| `LOCALHOST_PROXY_CONFIGURED` | Localhost proxy enabled |
| `LOCALHOST_PROXY_PORT_CHANGED` | Same mode, different loopback port |
| `PROXY_SERVER_CHANGED_TO_REMOTE` | Transition to non-loopback server (after non-empty) |
| `REMOTE_PROXY_CONFIGURED` | Remote proxy enabled from disabled/other state |
| `PAC_CONFIGURED` / `PAC_REMOVED` | AutoConfigURL added or removed |
| `REVERTER_SUSPECTED` | Repeated enable/disable loop (correlation only) |

Every event includes explainable output:

```json
{
  "primary_classification": "LOCALHOST_PROXY_REMOVED",
  "secondary_signals": ["LOCALHOST_PROXY_REMOVED", "REGISTRY_WRITER_PROOF_UNAVAILABLE"],
  "confidence_semantics": "ordinal_not_probability",
  "why": ["Evidence indicates localhost proxy server removal, not remote proxy configuration."],
  "limitations": ["Registry writer proof unavailable"],
  "unsafe_inferences_blocked": ["Remote proxy configured inference blocked because after_proxy_server is empty."]
}
```

Fixtures: `tests/fixtures/proxy_transitions/` · Tests: `tests/test_proxy_state_transitions.py`

## Coalescing

Rapid registry writes (e.g. `ProxyServer` cleared then `ProxyEnable` disabled) merge within `--coalesce-ms` (default **1000**, range **200–5000**):

```bash
python -m windows_network_toolkit proxy-watch --coalesce-ms 1000
```

Coalesced output includes:

```json
{
  "coalesced": true,
  "coalesce_window_ms": 1000,
  "raw_sub_event_count": 2
}
```

## Deterministic replay

```bash
python -m windows_network_toolkit proxy-replay --input tests/fixtures/proxy_loop.jsonl
```

Replay applies the same state machine, coalescing, control tests, and audit summary.

## Before / after example

### Incorrect (field-based diff)

```text
ProxyServer changed:
  before: 127.0.0.1:62285
  after: None

Risk: MEDIUM
Recommended policy action: alert — ProxyServer registry value mutated; Remote or non-loopback proxy server configured
```

### Correct (state transition engine)

```json
{
  "transition_class": "PROXY_SERVER_REMOVED_PARTIAL",
  "risk": "LOW",
  "proof_tier": "T1",
  "recommended_action": "observe — ProxyServer removed while ProxyEnable remained enabled",
  "limitations": [
    "Registry writer proof unavailable",
    "This event shows removal of ProxyServer, not remote proxy configuration"
  ],
  "policy_decision": "OBSERVE"
}
```

### Reverter loop (correlation only)

```json
{
  "transition_class": "REVERTER_SUSPECTED_LOCALHOST_PROXY_LOOP",
  "risk": "HIGH",
  "proof_tier": "T2",
  "recommended_action": "require human review — pattern suggests a proxy reverter or auto-reapply loop; this is correlation, not proof of registry write",
  "limitations": [
    "Pattern suggests a proxy reverter or auto-reapply loop",
    "This is correlation, not proof of registry write",
    "Collect Sysmon Event ID 13 or Procmon trace for registry writer proof"
  ]
}
```

## Audit controls

| Control ID | Purpose |
| --- | --- |
| `CTRL_PROXY_CLASSIFICATION_ACCURACY` | Removed server ≠ remote proxy |
| `CTRL_ATTRIBUTION_PROOF_BOUNDARY` | No registry writer claims below T3 |
| `CTRL_POLICY_GATE_NO_AUTONOMOUS_REMEDIATION` | Observe/alert/human-review only |
| `CTRL_COALESCING_REDUCES_FALSE_ALERTS` | Sub-events merge correctly |
| `CTRL_REVERTER_LOOP_PATTERN_DETECTION` | Repeated localhost cycles flagged |
| `CTRL_AUDIT_REPLAY_DETERMINISM` | Same input → same classification |

## Safety boundaries (unchanged)

No autonomous remediation: no silent registry edits, process killing, firewall reset, adapter disable, or VPN/security product disable. Risky actions remain dry-run + explicit human confirmation.
