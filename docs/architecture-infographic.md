# Architecture — Evidence Pipeline (Infographic)

**30-second read:** Windows endpoint observations flow through deterministic classification, policy gates, and audit export — never autonomous remediation.

## Mermaid flowchart

```mermaid
flowchart TB
    subgraph Collect["1. Collect (read-only)"]
        PS[proxy-status]
        PH[proxy-health]
        PW[proxy-watch]
        PO[proxy-owner]
    end

    subgraph Normalize["2. Normalize"]
        EE[EvidenceEvent T0–T5]
        PSM[proxy_state_machine]
    end

    subgraph Classify["3. Classify (deterministic)"]
        TC[Transition class + primary_classification]
        LIM[limitations[] + unsafe_inferences_blocked[]]
    end

    subgraph Govern["4. Govern"]
        CT[control_tests PASS/FAIL/PARTIAL]
        RS[risk_scores ordinal]
        PD[policy_decision OBSERVE/ALERT/HUMAN_REVIEW]
    end

    subgraph Audit["5. Audit & export"]
        JSONL[Hash-chained JSONL]
        GR[governance-report]
        PBI[powerbi-export star schema]
        API[GET /trisk/* read-only]
    end

    subgraph Blocked["Blocked by default"]
        KILL[process kill]
        FW[firewall reset]
        ADP[adapter disable]
        AUTO[autonomous registry mutation]
    end

    PS --> EE
    PH --> EE
    PW --> PSM
    PO --> EE
    EE --> PSM
    PSM --> TC
    TC --> LIM
    TC --> CT
    CT --> RS
    RS --> PD
    PD --> JSONL
    JSONL --> GR
    JSONL --> PBI
    GR --> API
    PD -.->|dry-run + typed confirm only| REM[proxy-disable preview]
    AUTO -.x Blocked
    KILL -.x Blocked
    FW -.x Blocked
    ADP -.x Blocked
```

## Layer placement (production stack)

| Production layer | This project |
|------------------|--------------|
| Observability & Logs | **Primary** — audit JSONL, proxy-watch, governance KPIs |
| Availability & Recovery | **Secondary** — dead-proxy diagnosis, gated remediation preview |
| APIs & Backend | Optional FastAPI `/trisk/*` (read-only) |
| Security & Data Access | Policy gates — not app IAM product |

## Related docs

- [domain-model.md](domain-model.md)
- [state-machine.md](state-machine.md)
- [faang-platform-review.md](faang-platform-review.md)
- [risk-control-framework.md](risk-control-framework.md)
