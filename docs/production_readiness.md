# Production readiness checklist

**Status:** Local-first **prototype** with production-**inspired** controls — not deployed enterprise software.

**Primary CLI:** `python -m windows_network_toolkit` (JSON-first) · Audit directory: `.audit/` (`WNT_AUDIT_DIR`)

---

## Deployment model

| Mode | Surface | Notes |
|------|---------|-------|
| Operator laptop | WNT JSON CLI | Default; dry-run on mutations |
| CI / Linux | Fixture inject (`--fixture`) | No live registry/network |
| Windows live | WNT CLI + optional `src` shim | Shim prints deprecation stderr |
| API (optional) | `backend/main.py` / Compose | Separate from WNT CLI path |

Hardening before enterprise rollout:

1. Enable RBAC on API writes (not WNT CLI alone)
2. Configure `WNT_AUDIT_DIR` to tamper-evident storage
3. Require Sysmon E13 for writer causation claims
4. Sign packages / service-wrap agent (roadmap)

---

## Safety model

| Guarantee | Implementation |
|-----------|----------------|
| Diagnose before repair | Default dry-run / PREVIEW; see [ADR-001](adr/ADR-001-diagnose-before-remediate.md) |
| No silent process kill | `process_kill_forbidden` registry tier; CLI requires Admin + typed confirm |
| No silent firewall reset | `firewall_reset_manual_only`; API execute blocked |
| No silent adapter disable | `adapter_disable_forbidden` |
| No registry mutation without confirmation | Typed phrases in registry + `validate_confirmation_phrase` |
| Listener correlation ≠ proof | [ADR-004](adr/ADR-004-heuristic-attribution-is-not-proof.md) |

Tests: `tests/test_policy_safety_contract.py`, `tests/test_safety_contract_extensions.py`, `tests/test_evidence_level_contract.py`, `tests/test_fixture_regression_demo.py`, `tests/test_safety_regression.py`, `tests/policy/`, `tests/api/`, `tests/windows_network_toolkit/test_safety_contract.py`.

WNT safety contracts enforce: dry-run default, `DISABLE_WININET_PROXY` token, no kill/firewall/adapter/WinHTTP mutation.

---

## Supported OS assumptions

| Surface | Assumption |
|---------|------------|
| Core CLI fixture diagnose | Cross-platform (Python 3.11+) |
| Live Windows probes | Windows 10/11 with standard user; Admin for stop-listener/reverter paths |
| Linux / Debian / Ubuntu / WSL | Observe-only via `platform_core/os_probe.py` — no live remediation |
| FastAPI `/platform/*` | Any OS; JSONL storage under `PLATFORM_DATA_DIR` |
| Docker Compose stack | See [production_deployment.md](production_deployment.md) — API, dashboard, Prometheus, Grafana, Loki |
| Sysmon / ETW proof | Optional Windows telemetry — not required for CI |

---

## Failure modes

- **Stale loopback proxy** — WinINET enabled while listener dead → browser fails, ping OK.
- **Proxy reverter respawn** — Parent PowerShell respawns `node.exe` → soak `REMEDIATION_NOT_STICKY`.
- **Policy drift on replay** — Embedded `policy_decision` differs from current registry → `changed_decisions` > 0.
- **Malformed JSONL** — Skipped lines; parse error counters increment.
- **RBAC denial** — HTTP 403; no mutation.

---

## Audit / replay guarantees

- Append-only JSONL writes (`platform_core.audit.write_audit`, CLI `logs/*.jsonl`, WNT `.audit/*.jsonl`).
- WNT audit soft-fail: write errors do not crash commands (`tests/windows_network_toolkit/test_audit_soft_fail.py`).
- Replay recomputes policy from stored signals — **no live reprobe** (`GET /platform/replay/{run_id}`).
- Determinism tested in `tests/test_replay_determinism.py`, `tests/replay/`.

---

## Policy guarantees

- ALLOW / PREVIEW / BLOCK from confidence + proof (`src/policy/hypothesis_gates.py`).
- Platform registry risk tiers + confirmation (`platform_core/remediation_registry.py`).
- Operator: preview + dry-run execute only; admin: live execute for allowlisted actions.

---

## Known limitations

- Confidence scores are **ordinal**, not calibrated probabilities.
- Heuristic attribution is triage-only without Sysmon/Procmon.
- Duplicate package trees (`proxy_guard/` vs `src/proxy_guard/`) — consolidation pending.
- JWT/Stripe routes in `backend/main.py` are demo scaffolding, not core product.

---

## What is not proven

- Which process wrote registry keys (without registry-write telemetry).
- Root cause from port listener alone.
- That a one-shot proxy disable stays sticky if reverter parent survives.

---

## Telemetry requirements

| Claim | Requires |
|-------|----------|
| Registry writer proof candidate | Sysmon 13/14, Security 4657, or Procmon CSV import |
| ETW-backed paths | Optional `evidence/etw_*` adapters |
| Default diagnose | Fixture or live probes only — no telemetry install |

---

## Intentionally blocked actions

- Arbitrary shell / commands
- Silent process kill
- Adapter disable via API
- Firewall reset via API live execute
- High/forbidden registry tiers without manual runbook

---

## Test coverage map

| Area | Tests |
|------|-------|
| Classification matrix (12 primaries) | `tests/platform_core/classification/` |
| WNT JSON CLI contract | `tests/windows_network_toolkit/test_cli_json_contract.py` |
| WNT proof envelope | `tests/windows_network_toolkit/test_diagnose_proof.py` |
| WNT audit soft-fail | `tests/windows_network_toolkit/test_audit_soft_fail.py` |
| Policy ALLOW/PREVIEW/BLOCK | `tests/test_policy_safety_contract.py`, `tests/policy/` |
| API dry-run default | `tests/test_api_dry_run_default.py`, `tests/api/` |
| Audit JSONL shape | `tests/test_audit_contract.py` |
| Replay determinism | `tests/test_replay_determinism.py`, `tests/replay/` |
| Registry writer proof | `tests/test_registry_writer_proof.py` |
| Proxy investigation | `tests/test_proxy_investigate.py` |
| Full suite | `pytest -q` (~550+ cases) |

CI smoke: `python -m windows_network_toolkit proxy-status --fixture tests/fixtures/enert/dead_proxy_59081.json`

---

## Roadmap

| Item | Status |
|------|--------|
| 12-label classification + proof envelope | **Done** |
| WNT JSON CLI + `.audit/` unification | **Done** |
| Sysmon/Event Log writer causation | Planned |
| Windows service mode | Planned |
| Signed packaging | Planned |
| Fleet aggregation / SIEM export | Planned |
| FastAPI local API extension | Partial (`windows_network_toolkit/platform/api.py`) |
| RBAC / Prometheus / policy-as-code | Planned |

See [faang-platform-engineering-positioning.md](faang-platform-engineering-positioning.md).

---

## Future multi-host architecture

- Opt-in `endpoint_agent` heartbeat → `POST /platform/agent/heartbeat`
- Snapshot ingest → incident clustering → `/platform/metrics`
- No default cloud upload ([ADR-005](adr/ADR-005-local-first-no-default-telemetry-upload.md))

See [faang_upgrade_audit.md](faang_upgrade_audit.md) for roadmap phases.
