# Proxy Transition State Machine

Deterministic classification from **full WinINET before/after state** (`windows_network_toolkit/proxy_state_machine.py`).

## Mermaid state diagram (simplified)

```mermaid
stateDiagram-v2
    [*] --> DISABLED
    DISABLED --> LOCALHOST_PROXY: enable + 127.0.0.1/::1 server
    DISABLED --> REMOTE_PROXY: enable + non-loopback server
    DISABLED --> PAC_CONFIGURED: AutoConfigURL set
    LOCALHOST_PROXY --> DISABLED: disable and/or server cleared
    LOCALHOST_PROXY --> LOCALHOST_PROXY: port change
    LOCALHOST_PROXY --> REMOTE_PROXY: server changed to remote
    REMOTE_PROXY --> PROXY_REMOVED: server cleared (NOT remote configured)
    LOCALHOST_PROXY --> PARTIAL_REMOVED: server cleared, enable still 1
    note right of PROXY_REMOVED
        after ProxyServer empty
        never classify as REMOTE_PROXY_CONFIGURED
    end note
    LOCALHOST_PROXY --> REVERTER_SUSPECTED: 3+ enable/disable cycles same port
```

## Transition classes (machine output)

| Class | Typical trigger |
|-------|-----------------|
| `LOCALHOST_PROXY_ENABLED` | Off → on with loopback server |
| `PROXY_SERVER_REMOVED_PARTIAL` | Server cleared, ProxyEnable still 1 |
| `PROXY_DISABLED_AND_SERVER_REMOVED` | Server cleared + ProxyEnable 0 |
| `PROXY_SERVER_CHANGED_TO_REMOTE` | Loopback → non-loopback (after non-empty) |
| `PAC_REMOVED` | AutoConfigURL cleared |
| `REVERTER_SUSPECTED_LOCALHOST_PROXY_LOOP` | Flapping pattern (correlation) |

## Explainable output shape

Every event includes `classification` with:

- `primary_classification`
- `secondary_signals[]`
- `confidence_semantics: ordinal_not_probability`
- `limitations[]`
- `unsafe_inferences_blocked[]`

## Tests

```powershell
pytest -q tests/test_proxy_state_transitions.py
```

## Related

- [proxy-state-transitions.md](proxy-state-transitions.md)
- [adr/0007-proxy-transition-full-state-classification.md](adr/0007-proxy-transition-full-state-classification.md)
