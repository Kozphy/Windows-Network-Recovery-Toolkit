# ADR-002: Policy-Gated Remediation (ALLOW / PREVIEW / BLOCK)

## Status

Accepted

## Context

Not every diagnostic finding should authorize repair. Destructive actions (firewall reset, adapter disable, arbitrary shell, silent process kill) must never run through automation. High-confidence heuristics without proof must not imply execute permission.

## Decision

Implement a dual-layer policy model:

1. **Hypothesis policy** (`src/policy/hypothesis_gates.py`) — ALLOW / PREVIEW / BLOCK from confidence + proof status.
2. **Remediation registry** (`platform_core/remediation_registry.py`) — risk tiers, typed confirmation phrases, surface rules, forbidden entries.

API and CLI execute paths consult both layers. **Operator role** may preview and dry-run; **admin role** may live-execute only allowlisted, non-manual actions with correct confirmation phrase.

## Consequences

- Every remediation attempt produces explicit `reason_codes` and audit rows.
- Forbidden tiers remain blocked even when `confidence=0.99` or role=admin.
- Portfolio demos can show “blocked unsafe action” without weakening production-inspired rules.

## Alternatives considered

| Alternative | Why rejected |
|-------------|--------------|
| RBAC-only (no registry) | Easy to add ad-hoc dangerous actions without review |
| YAML policy without code registry | Harder to test deterministically in CI |
| ML-driven auto-execute | Unexplainable; conflicts with epistemic boundaries |

## Risks

- Two policy vocabularies (hypothesis vs platform registry) can drift — mitigated by safety regression tests and ADR cross-links in docs.
