# ADR-011: Unified Domain Event Log for Technology Risk Loop

## Status

Accepted

## Context

The trisk pipeline has hash-chained audit JSONL and Postgres rows but no single timeline for agents, MCP, and UI.

## Decision

Introduce `src/platform_core/events/` with append-only `trisk_domain_events.jsonl` and optional `trisk_domain_events` Postgres table.

| Store | Purpose |
|-------|---------|
| Domain events | Operational timeline, MCP, UI |
| Audit chain | Governance hash chain |
| Postgres trisk_* | Queryable incidents |

## Consequences

- Emit from v1 ingest, worker, review, governance export
- Replay via `replay_events()` for tests
- Does not replace audit chain integrity model
