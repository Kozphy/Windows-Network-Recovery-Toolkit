# ADR-0008: Why This Is Not EDR

## Status

Accepted

## Context

Reviewers conflate endpoint proxy triage tooling with Endpoint Detection and Response (EDR), Extended Detection and Response (XDR), or antivirus products. Mispositioning fails both FAANG platform and Big 4 risk interviews.

## Decision

Explicitly scope the platform as **technology risk and endpoint reliability decision infrastructure**:

| Capability | This platform | EDR/XDR |
|------------|---------------|---------|
| Registry/proxy read | Yes | Often yes |
| Path probes | Yes | Varies |
| Malware verdict | **No** | Yes |
| Kernel telemetry | **No** | Yes |
| Autonomous containment | **No** | Yes |
| Threat intel feeds | **No** | Yes |
| Control test / ITGC narrative | **Yes** | Limited |
| Preview-only remediation gates | **Yes** | Varies |

Documentation, classifications, and governance report repeat non-claims. Classifications use reliability/triage labels (`DEAD_PROXY_CONFIG`, not `MALWARE_DETECTED`).

## Alternatives considered

| Alternative | Why rejected |
|-------------|--------------|
| Market as "lightweight EDR" | False advertising; wrong buyer expectations |
| Add signature scanning | Scope creep; duplicates AV |
| Remove security-adjacent classes entirely | Loses cyber triage workshop value |

## Consequences

- `UNKNOWN_LOCAL_PROXY` routes to human review — not auto-quarantine
- Portfolio targets platform eng + risk advisory — not SOC replacement
- Integration point with EDR is **export/correlation**, not replacement

## Security considerations

- Tooling must not weaken EDR by disabling security products
- Recommendations may suggest EDR correlation — not duplicate it

## Audit considerations

- CTRL-006 prevents malware verdict without writer proof
- Framework mapping cites ITGC themes, not MITRE-only SOC metrics

## What this prevents

- Buyer expectation of autonomous threat blocking
- Audit finding "claimed EDR without SOC controls"

## What this does not prove

- That endpoints are free of malware when proxy issue resolved
- Coverage equivalent to licensed EDR agent

## Interview defense

"This is the decision layer before remediation — evidence tiers, control tests, audit chain. EDR tells you threats; this tells you whether we're allowed to say what we know about proxy state and what fix is gated."
