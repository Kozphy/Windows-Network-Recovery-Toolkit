# ADR-004: Heuristic Attribution Is Not Proof

## Status

Accepted

## Context

Loopback proxy incidents often correlate a listening `node.exe` (or similar) with WinINET `ProxyServer=127.0.0.1:<port>`. Process/port correlation is useful for triage but does **not** establish registry-writer identity without registry-write telemetry.

## Decision

- Label listener/process correlation as **candidate evidence** or **inference**, never `CONFIRMED` registry writer proof.
- Registry-writer proof requires scoped telemetry (Sysmon Event 13/14, Security 4657, Procmon CSV import) via `evidence/registry_writer_proof.py`.
- Proof statuses: `CONFIRMED`, `REJECTED`, `INCONCLUSIVE`, `UNAVAILABLE` — propagated to JSON outputs and tests.
- Documentation and JSON `limitation` fields must state: *“listener/process correlation does not prove registry writer identity.”*

## Consequences

- UI and reports may show “suspected” actors without overclaiming.
- CI uses fixtures only; Sysmon is not required for default tests.
- Interview narrative stays credible under security review.

## Alternatives considered

| Alternative | Why rejected |
|-------------|--------------|
| Treat port owner as proof | False positives when proxy is re-enabled by unrelated parent |
| Hide attribution entirely | Reduces operator value for triage |
| Require Sysmon for all installs | Too heavy for local-first prototype |

## Risks

- Operators may ignore limitation text — mitigated by repeated docs, investigation bundle, and regression tests.
