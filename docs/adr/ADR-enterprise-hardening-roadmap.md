# ADR: Enterprise hardening roadmap (agent, observability, cross-platform foundation)

## Status

Accepted — 2026-06-12

## Context

The Windows Network Recovery Toolkit demonstrates an evidence-based endpoint reliability and technology risk analytics pipeline with policy-gated remediation previews, hash-chained audit, and deterministic replay. Portfolio reviewers and platform engineers ask for **production-shaped** capabilities: deployable read-only agents, observability, scale/concurrency hardening, cross-platform evidence foundations, packaging, security review artifacts, and rollback governance.

The repository must **not** drift into EDR, malware detection, or autonomous remediation positioning ([ADR-0008](0008-why-this-is-not-edr.md), [ADR-012](ADR-012-agent-contracts-not-autonomous-execution.md)).

Existing assets:

- `endpoint_agent/` — observe-only prototype with JSONL output
- `platform_core/network_diagnostics/` — Windows / Linux / generic providers
- `backend/prometheus_exporter.py` — partial metrics surface
- `src/platform_core/remediation/rollback.py` — preview-oriented rollback planning
- Safety contract CI and threat-model documentation

A monolithic “implement everything” change would risk breaking CLI compatibility, safety gates, and 1,500+ tests.

## Decision

Adopt an **eight-phase hardening program** documented in [enterprise-hardening-roadmap.md](../enterprise-hardening-roadmap.md). Implement **one phase at a time**; Phase 1 delivers interfaces only.

### Why add an agent layer

- **Problem:** CLI-only collection does not model fleet evidence ingest or scheduled observe-only telemetry.
- **Decision:** Extend `endpoint_agent/` with a read-only local agent that spools normalized evidence to JSONL and optional health endpoints.
- **Constraint:** Agent collection is **read-only by default** — no registry mutation, process kill, firewall reset, adapter disable, or remediation execution in the agent process. Repair remains in policy-gated CLI paths with typed human confirmation.

### Why agent collection is read-only by default

- Aligns with [ADR-001](ADR-001-diagnose-before-remediate.md) and [ADR-002](0002-policy-gated-remediation.md).
- Prevents “helpful” autonomous fixes that bypass audit and human review.
- Reduces attack surface: a compromised agent cannot mutate host state if it never holds execute authority.
- Matches `endpoint_agent/collector_abstraction.py` and `AGENTS.md` safety conventions.

### Why remediation remains policy-gated

- Observation ≠ proof; classification ≠ accusation; policy ALLOW ≠ safety guarantee.
- Typed confirmation tokens (`DISABLE_WININET_PROXY`, `APPLY_CHATGPT_LOW_RISK`) and dry-run defaults are **non-negotiable** contract tests.
- Agent and observability layers **must not** weaken `windows_network_toolkit/safety.py` or platform policy engines.

### Why observability is added

- Production-shaped platforms require **correlation** across evidence ingest, classification, policy decisions, and audit writes.
- Structured logs, Prometheus counters, and `trace_id` / `audit_id` propagation support debugging and committee reconstruction without claiming formal SIEM replacement.
- Metrics describe **platform behavior** (events collected, previews, blocked actions) — not security verdicts.

### Why Linux/macOS support starts as evidence abstraction, not full parity

- WinINET/WinHTTP/registry-writer proof tiers are **Windows-specific**. Pretending parity would produce false confidence and violate epistemic boundaries.
- Linux/macOS collectors expose **PARTIAL** support: environment proxy variables, DNS, listening-port hints, and explicit `limitations[]`.
- Unknown platforms return **NOT_SUPPORTED** rather than fabricated observations.
- Canonical seam: `src/platform_core/evidence_collection/` delegating to `platform_core/network_diagnostics/` — not a duplicate collector tree under `windows_network_toolkit/`.

### Why packaging is separated from execution authority

- Installers (pipx, wheel, zip, optional service wrappers) distribute **binaries and docs** — they do not grant remediation authority.
- Auto-start services and silent elevation are **opt-in** and documented; default install remains manual, dry-run-first.
- Signing, SBOM, and release channels are distribution concerns; policy gates remain in code and tests regardless of packaging channel.

## Consequences

### Positive

- Incremental, reviewable diffs per phase
- Clear portfolio vs production scope boundaries
- Reuses existing Windows collectors and safety contracts
- Cross-platform honesty via `FULL` / `PARTIAL` / `NOT_SUPPORTED` labels

### Negative

- Temporary duplication between `endpoint_agent/` and new evidence_collection until Phase 2 wiring
- Linux/macOS classifications carry heavier `limitations[]` — may look “incomplete” to casual reviewers (intentional)
- Full production fleet ingest, signed agents, and live rollback remain **out of scope** for the portfolio program

## Alternatives considered

| Alternative | Rejected because |
|-------------|------------------|
| Big-bang rewrite to microservices | Breaks CLI compatibility and safety CI |
| Skip agent layer; API-only ingest | Does not demonstrate endpoint deployment story |
| Full Linux WinINET emulation | False parity; misleading proof tiers |
| Bundle remediation into agent MSI | Conflates distribution with execution authority |
| Defer observability | Cannot demonstrate production-shaped operability |

## References

- [enterprise-hardening-roadmap.md](../enterprise-hardening-roadmap.md)
- [production-readiness-gap.md](../production-readiness-gap.md)
- [agent-workflow-spec.md](../agent-workflow-spec.md)
- [AGENTS.md](../../AGENTS.md)
