# ADR-001: Diagnose Before Remediate

## Status

Accepted

## Context

Windows endpoint failures often present as “online but broken” (browser/proxy/DNS path). Blind repair scripts mutate registry, firewall, or stack settings without structured evidence, increasing blast radius and making post-incident review difficult.

## Decision

All remediation paths must be preceded by read-only diagnosis that produces structured observations, hypotheses, and policy evaluation. Repair commands default to **dry-run** or **PREVIEW**; live mutation requires explicit operator confirmation and allowlisted actions.

## Consequences

- Operators spend more steps before repair, but every step is auditable.
- CLI and API surfaces expose diagnosis artifacts (`reports/`, JSONL) before execute endpoints accept work.
- Beginner `.bat` wrappers remain as entry points; they delegate to the same diagnose-first handlers where wired.

## Alternatives considered

| Alternative | Why rejected |
|-------------|--------------|
| Auto-repair on high confidence | Violates safety posture; confidence is ordinal, not calibrated probability |
| Single “fix network” button | Hides layer separation and policy gates |
| Cloud-only diagnosis | Conflicts with local-first, air-gapped operator requirements |

## Risks

- Operators may skip diagnosis if docs are unclear — mitigated by demo path and blocked execute without preview linkage on API routes.
- Multiple CLI entrypoints could confuse — mitigated by unified narrative in README and `docs/demo_3_minute.md`.
