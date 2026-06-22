# ADR-013: MCP Read-Only Policy Gate

## Status

Accepted

## Context

MCP exposes platform data to AI clients. Writes must not bypass policy registry.

## Decision

- `MCP_READ_ONLY=1` default
- Phase 3 tools: read/search/report only
- Each call logs `McpToolInvoked` domain event
- No remediation or ingest MCP tools

## Consequences

- AI clients cannot execute registry mutations via MCP
- Future write tools require separate ADR + policy integration
