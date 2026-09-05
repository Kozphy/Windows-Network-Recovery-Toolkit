# ADR-017: Unified operator incident card

## Status

Accepted — 2026-08-15

## Context

Operators ran four parallel diagnoses (proxy guardian, rewriter containment, network-path-health, browser stall) and could declare the host healthy when WinINET was direct while IPv6/QUIC still stalled.

## Decision

1. One read-only compose envelope (`operator_incident_card.v1`) is the operator contract across CLI surfaces.
2. Deterministic priority: rewriter match > dead/stale/broken proxy > IPv6 / Happy Eyeballs > browser QUIC stall > healthy.
3. `limitations[]` from every source are unioned and never dropped.
4. `recommended_next_command` is always **preview-first**; the card never applies remediation.
5. `sli_hints` map the primary class to local operator SLIs (time-to-direct, false-clear, dual-stack, blocked high-risk).
6. Classifier may emit `IPV6_BROKEN_IPV4_OK`, `HAPPY_EYEBALLS_STALL`, `BROWSER_QUIC_STALL` when proxy is not the high-severity blocker.

## Consequences

- `python -m src operator-incident --fixture …` is the CI-safe surface.
- Live gather on Windows is optional; Linux/CI uses fixtures only.
- False-clear is an SLO, not a vibe.

## What this does not prove

Root cause, malware, or that following the next command will restore the browser path.
