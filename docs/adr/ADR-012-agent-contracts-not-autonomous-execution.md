# ADR-012: Agent Contracts Without Autonomous Execution

## Status

Accepted

## Context

AI-native positioning must not imply autonomous remediation or security verdicts.

## Decision

- Phase 1: Pydantic contracts in `src/platform_core/agents/contracts/`
- Orchestrator calls **existing deterministic** `analytics_pipeline`
- No LLM tool-calling loop until Phase 6 (deferred)
- Human review module gates accusatory-adjacent classes

## Consequences

- Agent JSON is audit-friendly interchange format
- Explanation guardrails remain authoritative for any LLM text
