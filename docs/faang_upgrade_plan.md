# FAANG-style Endpoint Reliability upgrade (additive)

This iteration layers a **unified normalized event envelope**, JSONL **event bus**, attribution **provider stubs**, RBAC-aware **policy gate** evaluation, deterministic **replay**, and guarded **dashboard/API** surfaces atop the existing beginner `.bat` flows (unchanged) and legacy `failure_system` tooling.

Goals:

| Layer | Outcome |
| --- | --- |
| Events (`platform_core/events.py`) | Stable schema for dashboards, audits, and offline replay |
| Bus (`platform_core/event_bus.py`) | Append/read with schema validation & tolerant parsers |
| Attribution (`platform_core/attribution/`) | Explicit confidence ladder — no fake forensic proof |
| Policy gate (`platform_core/policy/engine.py`) | Split **preview vs live execute** defaults (deny-by-default live) |
| Replay (`platform_core/replay`) | Compare historical vs recomputed gates with zero mutations |
| API | `/platform/events`, `/platform/policy/summary`, `/platform/replay/preview` |

Deterministic JSON samples live under **`tests/fixtures/platform/*.json`** (normalized envelopes) —
keep agent evidence fixtures (**`tests/fixtures/healthy_network.json`**, DNS/proxy/tcp issue files, …)
distinct to avoid accidental schema collisions.

Non-goals:

- Hosted multi-tenant auth, IdP federation, outbound log shipping
- Automated destructive repair (`firewall`/adapter resets remain blocked or manual-only)
- Embedding API secrets in-repo
