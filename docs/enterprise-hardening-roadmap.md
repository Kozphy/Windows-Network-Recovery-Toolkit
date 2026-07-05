# Enterprise hardening roadmap

**Status:** Active plan — portfolio prototype evolving toward production-shaped endpoint reliability / technology risk analytics.

**Positioning (non-negotiable):** This platform is **not** antivirus, EDR, XDR, MITM detection, malware detection, or autonomous remediation. It collects **evidence**, classifies reliability signals with explicit `limitations[]`, gates remediation behind human confirmation, and exports audit-backed governance analytics.

**Related:** [production-readiness-gap.md](production-readiness-gap.md) · [ADR-enterprise-hardening-roadmap.md](adr/ADR-enterprise-hardening-roadmap.md) · [AGENTS.md](../AGENTS.md)

---

## Current state summary

| Area | What exists today | Maturity |
|------|-------------------|----------|
| Windows evidence | `windows_network_toolkit/collectors/`, WinINET/WinHTTP probes, proxy state machine | **Strong** (portfolio-ready with fixtures) |
| Cross-platform observe | `platform_core/network_diagnostics/` (Windows / Linux / generic macOS fallback) | **Foundation** |
| Endpoint agent | `endpoint_agent/` — read-only cycles, JSONL spool, optional HTTP sync | **Prototype** |
| Decision pipeline | `src/platform_core/` — evidence tiers, policy, audit, replay | **Canonical** |
| Backend API | FastAPI `backend/` — `/trisk/*`, `/platform/*`, Prometheus `/metrics` | **Demo + partial production shape** |
| Fleet / scale | `fleet-simulate`, `platform_core/fleet*`, `tests/test_fleet_scale.py` | **Synthetic / contract tests** |
| Observability | `src/platform_core/operability/` + `backend/prometheus_exporter.py`, `/metrics` merge | **Local** — structured JSON logs, trace/audit propagation, in-memory counters |
| Security pack | `docs/threat-model.md`, `tests/security/`, safety contract CI | **Portfolio-grade** — no formal pen test |
| Rollback | `src/platform_core/remediation/rollback.py`, `RemediationPreview.rollback_preview` | **Preview-first** — six-part package; no live executor in platform core |
| Packaging | `pip install -e ".[dev]"`, Docker compose, Makefile | **Dev-first** — no signed MSI/wheel release pipeline |
| CLI version | `pyproject.toml` `0.2.0`; no `version` subcommand | **Gap** |

**Safety contracts enforced in CI:** `tests/test_policy_safety_contract.py`, `tests/test_proxy_classifier_safety_contract.py`, `tests/security/`, `make principles-test`.

---

## Target production-shaped architecture

```text
┌─────────────────────────────────────────────────────────────────────────┐
│  Operator / committee UI (optional Next.js) + Power BI star-schema CSV   │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │
┌───────────────────────────────▼─────────────────────────────────────────┐
│  FastAPI platform (backend/) — ingest, policy preview, metrics, audit    │
│  Human review queue · typed confirmation tokens · dry-run default          │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        │                       │                       │
┌───────▼────────┐   ┌────────▼────────┐   ┌─────────▼──────────┐
│ Read-only      │   │ Canonical       │   │ Observability      │
│ endpoint agent │   │ decision engine │   │ logs · metrics ·   │
│ JSONL spool    │   │ src/platform_   │   │ trace_id / audit_id│
│ heartbeat      │   │ core/           │   │ Prometheus /metrics│
└───────┬────────┘   └────────┬────────┘   └────────────────────┘
        │                       │
┌───────▼───────────────────────▼─────────────────────────────────────────┐
│  OS evidence abstraction (src/platform_core/evidence_collection/)        │
│  Windows FULL · Linux/macOS PARTIAL · unknown NOT_SUPPORTED              │
└───────┬─────────────────────────────────────────────────────────────────┘
        │
┌───────▼─────────────────────────────────────────────────────────────────┐
│  OS-specific collectors (delegate — do not duplicate WNT registry stack)   │
│  Windows: network_diagnostics.windows + windows_network_toolkit/         │
│  Linux: env proxy, resolv.conf, optional linux_proxy_snapshot            │
│  macOS: env proxy + explicit limitations (no WinINET claims)             │
└─────────────────────────────────────────────────────────────────────────┘
```

**Human-in-the-loop remains mandatory** at policy preview, confirmation, and execute boundaries.

---

## Portfolio scope vs production scope

| Capability | Portfolio scope (this repo) | Production scope (out of band / future) |
|------------|----------------------------|----------------------------------------|
| Agent deployment | Local read-only agent, JSONL spool, docs | Signed MSI, Intune, fleet MDM, mTLS ingest |
| Scale claims | Synthetic 100–10k fixture fleet tests | Proven multi-tenant Kafka/EventStore ingest |
| Observability | Structured logs + Prometheus counters | Hosted APM, SLO paging, log retention legal hold |
| Linux/macOS | Evidence abstraction + PARTIAL collectors | Parity with Windows proof tiers |
| Packaging | pipx/wheel/zip docs + smoke tests | Authenticode, SBOM, GitOps signed images |
| Security review | Threat model + abuse-case tests | Formal pen test, SOC 2 control mapping |
| Rollback | Preview + audit record model | Live reversible executor with operator runbook |

Do **not** claim enterprise fleet scale or malware detection unless tests and docs explicitly support the claim.

---

## Feature-by-feature implementation plan

### Phase 1 — Architecture and interfaces (done)

| Deliverable | Path |
|-------------|------|
| Evidence collection contracts | `src/platform_core/evidence_collection/` |
| Platform support levels | `FULL`, `PARTIAL`, `NOT_SUPPORTED` |
| Factory | `get_endpoint_evidence_collector()` |
| Tests | `tests/platform_core/evidence_collection/` |
| Windows | Delegates to `platform_core.network_diagnostics` — unchanged behavior |
| Linux / macOS | `PARTIAL` with explicit limitations; no WinINET/WinHTTP claims |
| Unknown OS | `NOT_SUPPORTED` — empty observations, documented limitations |

### Phase 2 — Agent deployment MVP (done)

| Deliverable | Path |
|-------------|------|
| CLI | `agent run`, `agent once`, `agent health`, `agent spool-status` |
| Read-only agent loop | `windows_network_toolkit/agent/` — spool only, no remediation |
| Local health endpoint | Optional `127.0.0.1` HTTP health (read-only status) |
| Docs | `docs/agent-deployment.md` |
| Tests | `tests/windows_network_toolkit/test_read_only_agent.py` |

### Phase 3 — Metrics / logs / tracing (done)

| Deliverable | Path |
|-------------|------|
| Structured JSON logging | `src/platform_core/operability/structured_logging.py` |
| Metric counters | `src/platform_core/operability/metrics_registry.py` + `events.py` |
| Prometheus | Merged into `GET /metrics` in `backend/main.py` |
| Trace propagation | `trace_id` / `audit_id` via `context.py`; agent + `append_jsonl` |
| Docs | `docs/observability.md` |
| Tests | `tests/platform_core/operability/test_observability.py` |

### Phase 4 — Scale testing and concurrency (done)

| Deliverable | Path |
|-------------|------|
| Fleet fixtures | 100 / 1k / 10k synthetic endpoint event records |
| Concurrency tests | ingest, JSONL append, hash-chain, spool read/write |
| Docs | `docs/scale-testing.md` |
| Tests | `tests/scale/`, `tests/concurrency/` |
| File locks | `src/platform_core/io/locked_jsonl.py` (`fcntl` / `msvcrt`) |

### Phase 5 — Linux/macOS foundation (done)

| Deliverable | Path |
|-------------|------|
| OS abstraction docs | `docs/cross-platform-support.md` |
| Linux collector depth | env proxy, gsettings/NM hints, listening ports |
| macOS collector depth | `networksetup` hints, env proxy, listening ports |
| Fixture tests | `tests/fixtures/cross_platform/` |
| Normalization | `src/platform_core/evidence_collection/normalize.py` |
| Labeling | Every non-Windows classification includes `limitations[]` |

### Phase 6 — Packaging / installer (done)

| Deliverable | Path |
|-------------|------|
| Strategy doc | `docs/packaging-installer.md` |
| pipx / wheel / Windows zip | Documented in strategy doc + `scripts/run-portable-wnrt.ps1` |
| Service plans | Windows service, systemd, launchd — **documented opt-in only** |
| CLI | `version` subcommand + `wnrt` console script |
| Smoke test | `tests/packaging/test_entrypoint_smoke.py` |

### Phase 7 — Security review pack (done)

| Deliverable | Path |
|-------------|------|
| Consolidated pack | `docs/security-review.md` |
| Topics | assets, boundaries, threat model, abuse cases, policy gates, audit, supply chain, secrets |
| Tests | `tests/security/test_security_review_pack.py` + existing safety contract suite |
| Preserve | `tests/test_policy_safety_contract.py`, `tests/security/`, governance audit tests |

### Phase 8 — Rollback strategy (done)

| Deliverable | Path |
|-------------|------|
| Docs | `docs/rollback-strategy.md` |
| Model | pre-change snapshot, preview record, approval token, rollback preview, audit row |
| Code | `src/platform_core/remediation/rollback.py`, `RemediationPreview.rollback_preview` |
| Tests | `tests/platform_core/remediation/test_rollback_preview.py` — **no live mutation tests** |

---

## Proposed modules / files (cumulative)

```text
src/platform_core/evidence_collection/     # Phase 1
  __init__.py
  models.py
  base.py
  windows.py
  linux.py
  darwin.py
  unsupported.py
  factory.py

endpoint_agent/                            # Phase 2 (extend)
  spool.py                                 # optional refactor
windows_network_toolkit/cli.py             # agent * subcommands

src/platform_core/operability/             # Phase 3
  structured_logging.py
  metrics_registry.py

tests/platform_core/evidence_collection/   # Phase 1
tests/scale/                               # Phase 4
tests/concurrency/                         # Phase 4

docs/agent-deployment.md                   # Phase 2
docs/observability.md                      # Phase 3 (may extend existing)
docs/scale-testing.md                      # Phase 4
docs/cross-platform-support.md             # Phase 5
docs/packaging-installer.md                # Phase 6
docs/security-review.md                    # Phase 7
docs/rollback-strategy.md                  # Phase 8
```

**Do not duplicate** `windows_network_toolkit/collectors/` — delegate from abstraction layer.

---

## Security boundaries

| Boundary | Enforcement |
|----------|-------------|
| No autonomous remediation | Policy engine + dry-run default + confirmation tokens |
| Blocked actions | `KILL_PROXY_PROCESS`, `FIREWALL_RESET`, `ADAPTER_DISABLE`, `WINHTTP_MODIFY` |
| Agent read-only default | No registry writes, no process kill in agent loops |
| Classification ≠ accusation | Reliability labels only; no malware verdict strings |
| AI ≠ execution authority | Explanation contracts; human approve for apply |
| Audit tamper detection | Hash-chained JSONL tests must keep passing |
| MCP / API read-only default | `MCP_READ_ONLY=1`; no execute tools without explicit gate |

---

## Test strategy

| Layer | Approach |
|-------|----------|
| Unit | Pure functions, fixture payloads, forced `os_family` in factory |
| Safety contracts | Existing `test_policy_safety_contract.py` — never weaken |
| Integration | Fixture replay; Windows-only tests gated with `skipif` |
| Scale | Synthetic records only — document as local/synthetic scale |
| Concurrency | Deterministic thread/process tests with temp dirs |
| CI | `pytest -q` + targeted slices; `ruff check` on touched paths |

**Validation commands (Windows):**

```powershell
pip install -r requirements.txt
pytest -q tests/platform_core/evidence_collection/
make principles-test
ruff check src/platform_core/evidence_collection/
```

---

## Rollback strategy (target model)

Remediation remains **preview-only by default**. Rollback is a **governance artifact**, not silent undo:

1. **Pre-change evidence snapshot** — hash-linked observation bundle before any approved apply.
2. **Planned mutation preview** — structured intended registry/command deltas (dry-run output).
3. **Reversible action record** — action_id, confirmation token, operator identity, timestamp.
4. **Human approval token** — typed phrase per action class (`DISABLE_WININET_PROXY`, etc.).
5. **Rollback preview** — read-only plan to restore LKG or documented safe state.
6. **Rollback audit row** — append-only JSONL; no execute without second confirmation.

Live rollback execution is **out of scope** until explicit operator runbooks and safety review approve it.

---

## Explicit non-claims

- Does **not** detect compromise, malware, or MITM attacks.
- Does **not** provide autonomous remediation or AI-authorized execute.
- Does **not** guarantee enterprise fleet scale without measured ingest benchmarks.
- Does **not** replace EDR, antivirus, or formal audit opinions.
- Confidence scores are **ordinal**, not calibrated probabilities.
- Linux/macOS paths are **experimental foundation** — not WinINET parity.

---

## Definition of done (program-level)

| Phase | Done when |
|-------|-----------|
| **1** | Factory + collectors + tests green; Windows unchanged; non-Windows labeled PARTIAL/NOT_SUPPORTED |
| **2** | Agent CLI read-only; spool + health; docs + tests |
| **3** | Metrics counters + trace_id propagation tested; `/metrics` exposes new series |
| **4** | Scale + concurrency tests pass; docs state synthetic/local limits |
| **5** | Cross-platform fixtures + limitations on every non-Windows output |
| **6** | Packaging doc + version command + smoke test |
| **7** | `security-review.md` + no regression in safety contract CI |
| **8** | Rollback preview tests + doc; no live mutation in tests |

**Program complete (production-shaped portfolio):** Phases 1–8 docs and tests green; `pytest -q` passes; safety contracts unchanged; README non-claims preserved.

---

## Phase status tracker

| Phase | Status |
|-------|--------|
| 1 — Interfaces | **Started** (`src/platform_core/evidence_collection/`) |
| Phase 2 — Agent MVP | **Done** (`windows_network_toolkit/agent/`, `docs/agent-deployment.md`) |
| 3 — Observability | Planned |
| 4 — Scale / concurrency | Planned |
| 5 — Cross-platform | Planned |
| 6 — Packaging | Planned |
| 7 — Security review | Planned |
| 8 — Rollback | **Done** (`docs/rollback-strategy.md`, `test_rollback_preview.py`) |
