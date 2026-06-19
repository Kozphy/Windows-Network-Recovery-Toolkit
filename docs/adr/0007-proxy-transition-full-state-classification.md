# ADR-0007: Proxy Transition Full-State Classification

## Status

Accepted

## Context

WinINET proxy registry changes are multi-field (ProxyEnable, ProxyServer, PAC, AutoDetect). Classifying from isolated field diffs produces dangerous false positives — e.g. labeling empty ProxyServer after removal as "remote proxy configured."

## Decision

`proxy_state_machine.classify_transition()` requires **full before/after** normalized `ProxyWininetState`:

- `TransitionClass` enum covers enable/disable, server removal partial, localhost enable, PAC, mismatch, reverter loop
- `PrimaryClassification` provides interview-grade labels
- `FORBIDDEN_CLASSIFICATIONS_WHEN_AFTER_SERVER_EMPTY` blocks remote labels when server empty
- `validate_classification_safety()` returns violations list
- `build_explainable_classification()` emits `why[]`, `unsafe_inferences_blocked[]`
- Coalescing merges rapid sub-events within window (default 1000 ms)
- Reverter detection is pattern-based over timeline — separate transition class

**Doctrine:** Observation is not proof. Classifications never use single-field mutation alone.

## Alternatives considered

| Alternative | Why rejected |
|-------------|--------------|
| Diff-only ProxyServer field | Caused remote misclassification on removal |
| Free-text LLM labels | Non-deterministic; audit unsafe |
| Ignore WinHTTP in transition | Misses `WININET_WINHTTP_MISMATCH` class |

## Consequences

- More code in state machine — justified by safety tests
- `ERROR_INSUFFICIENT_DATA` when before/after incomplete
- Confidence values are ordinal weights per transition type

## Security considerations

- Blocks remote proxy inference when evidence shows removal
- Reverter class requires human review policy decision

## Audit considerations

- Auditors can replay before/after dicts from transition events
- Secondary signals document listener and path state without upgrading tier

## What this prevents

- False "remote proxy configured" on cleanup events
- Malware narrative from enable bit flip alone

## What this does not prove

- Registry writer identity (requires T4 telemetry)
- That coalescing window captures all vendor-specific multi-write patterns

## Interview defense

"I classify from full before/after state — if after ProxyServer is empty, the code forbids remote proxy labels. That's a test-backed safety rule, not documentation fluff."
