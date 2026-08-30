# ADR: Deterministic Remediation Boundary

- Status: Accepted
- Context: Portfolio / production-shaped prototype

## Context

The platform can use AI or other non-deterministic components to help explain collected evidence. Endpoint remediation, however, changes machine state and must remain predictable, reviewable, testable, and attributable.

Allowing generated text or an LLM decision to directly authorize a registry/network mutation would merge explanation, authorization, and execution into one trust boundary. That makes negative testing, audit reconstruction, least privilege, and failure analysis materially harder.

## Decision

AI-assisted output may explain evidence or propose a candidate action, but it MUST NOT authorize or directly execute endpoint mutation.

Mutation follows this boundary:

```text
Evidence -> deterministic classification -> policy evaluation
         -> explicit approval where required -> allowlisted deterministic executor
         -> post-action verification -> audit record
```

The default posture is preview/dry-run. Execution must use an allowlisted operation with validated parameters. Missing evidence, missing approval, invalid parameters, or an unsupported state fails closed.

## Consequences

### Positive
- deterministic safety-contract tests are possible;
- authorization is attributable to policy/operator state rather than generated prose;
- prompt injection cannot directly become an execution authorization;
- rollback and verification can be modeled around known operations;
- audit records can identify the exact transition and executor.

### Negative
- less autonomous than an agent that can freely choose tools;
- new remediation types require explicit implementation and tests;
- human approval can add operational latency.

## Alternatives considered

### LLM directly chooses and executes remediation
Rejected for this project because the safety and audit boundary is too weak for endpoint mutation.

### LLM chooses from an unrestricted shell/tool surface
Rejected because an allowlist provides a smaller, testable execution surface.

### Fully manual remediation
Safer but does not demonstrate policy-gated automation or deterministic verification. Retained as a fallback operational mode rather than the primary architecture.

## Verification

The repository should maintain negative tests proving that absent approval/policy permission cannot cross the mutation boundary, plus positive tests proving that an allowlisted operation can be verified and audited when all prerequisites are satisfied.
