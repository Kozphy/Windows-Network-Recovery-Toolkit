# Google L11 reference (not a claim)

**Status:** Reference document. This repository does **not** claim Google L11 (Senior Fellow) scope or influence.

Google L11 is org-wide technical direction: multi-product standards, industry papers, and influence measured in years and organizations — not a local CLI milestone. Treating this toolkit as “L11-complete” would be false certainty.

What we **do** implement here is a **Staff (L6)** and **Senior Staff (L7)** bar on a Technology Risk & Control Analytics prototype: contracts, SLOs, safety gates, and ADRs that other surfaces must follow.

See also: [faang-platform-review.md](faang-platform-review.md) · [production-readiness-gap.md](production-readiness-gap.md) · [slo-endpoint-reliability.md](slo-endpoint-reliability.md) · [AGENTS.md](../AGENTS.md).

## Level map (behaviors vs claims)

| Google-style level | Behaviors this repo can demonstrate | What we must not claim |
|--------------------|-------------------------------------|------------------------|
| L5 Senior | Fixture-first tests, JSON CLI, dry-run defaults, `limitations[]` | Production-certified product |
| **L6 Staff (implemented bar)** | Unified operator incident card, SLO/SLI definitions, CI-gated replay + classifier eval, policy-gated remediation, hash-chained audit | Fleet SLOs, 99.9% availability, PagerDuty |
| **L7 Senior Staff (implemented bar)** | ADRs that bind CLI / `.cmd` / classifier; Prefer-IPv4 blast radius; no silent process kill; multi-surface compose without false-clear | Org-wide platform mandate; 100k-endpoint Kafka |
| L8 Staff+ / Principal | Multi-tenant control plane, auth, WORM, signed agents | **Out of this pass** — see gap table |
| **L11 Senior Fellow** | Industry-scale influence, papers, multi-org standards | **Out of scope.** Reference only. |

## L6 substance in this repo

- Unified operator contract: `python -m src operator-incident` ([`src/proxy_drift/operator_incident_card.py`](../src/proxy_drift/operator_incident_card.py))
- Classifier reliability labels (not malware): `IPV6_BROKEN_IPV4_OK`, `HAPPY_EYEBALLS_STALL`, `BROWSER_QUIC_STALL`
- Local operator SLOs: [slo-endpoint-reliability.md](slo-endpoint-reliability.md)
- CI job `eval-benchmarks` in [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) — replay + classifier thresholds
- Safety: `KILL_PROXY_PROCESS` remains blocked; typed tokens for apply

## L7 substance in this repo

- [ADR-015](adr/ADR-015-no-silent-kill-rewriter-containment.md) — containment ≠ silent kill
- [ADR-016](adr/ADR-016-prefer-ipv4-blast-radius.md) — dual-stack mitigation blast radius
- [ADR-017](adr/ADR-017-unified-operator-incident-card.md) — one card across proxy / path / browser

Fleet-scale ADR [ADR-008](adr/ADR-008-fleet-scale-100k-endpoints.md) stays **Proposed**. Auth, WORM, and Kafka are documented gaps, not stubs that pretend to exist.

## Non-claims (repeat)

Observation ≠ proof · Correlation ≠ causation · Classification ≠ accusation · Policy allow ≠ safety guarantee · Dry-run default.
