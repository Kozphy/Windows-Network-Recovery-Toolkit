# Reliability Platform — Sequence & State Diagrams

## Decision pipeline (sequence)

```mermaid
sequenceDiagram
    participant Src as Telemetry Sources
    participant Pipe as Event Pipeline
    participant SM as State Machine
    participant Hyp as Hypothesis Engine
    participant EG as Evidence Graph
    participant Pol as Policy Engine
    participant Dec as Decision Engine
    participant Aud as Signed Audit
    participant Rep as Replay Engine

    Src->>Pipe: raw observation
    Pipe->>Pipe: normalize → NormalizedPlatformEvent
    Pipe->>SM: event batch
    SM->>SM: deterministic transitions
    SM->>Hyp: state path + events
    Hyp->>Hyp: weighted ranking
    Hyp->>EG: hypotheses + events
    EG->>Pol: graph summary
    Pol->>Dec: ALLOW / PREVIEW / BLOCK
    Dec->>Aud: PlatformDecisionRecord + HMAC
    Aud->>Rep: append-only store
    Rep->>Rep: time-travel parity check
```

## State machine

```mermaid
stateDiagram-v2
    [*] --> NORMAL
    NORMAL --> LOCAL_PROXY_ENABLED: localhost_proxy_enabled
    LOCAL_PROXY_ENABLED --> PROXY_FAILURE: browser_https_failed
    PROXY_FAILURE --> BYPASS_SUCCESS: proxy_bypass_succeeded
    BYPASS_SUCCESS --> ROOT_CAUSE_IDENTIFIED: proof_confirmed OR sysmon_registry_write
    BROKEN --> RECOVERING: proxy_disabled
    RECOVERING --> NORMAL: browser_https_ok
    LOCAL_PROXY_ENABLED --> DEGRADED: optional drift signals
    DEGRADED --> BROKEN: sustained failure
```

## Evidence graph node kinds

| Kind | Example |
|------|---------|
| `process` | node.exe ← powershell.exe |
| `registry_write` | ProxyEnable=1 |
| `listener` | 127.0.0.1:61187 |
| `network_flow` | HTTPS failure via proxy path |
| `policy_decision` | PREVIEW — unproven high confidence |
| `hypothesis` | Known developer tool (ordinal 0.72) |

## API surfaces

| Version | Base path | Purpose |
|---------|-----------|---------|
| v1 | `/platform/*` | Fleet, incidents, remediation preview |
| v2 | `/platform/v2/*` | Events, decisions, replay, policies |
