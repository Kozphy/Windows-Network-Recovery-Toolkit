# ERP Upgrade — File-by-File Implementation Plan

This document maps the 10-phase upgrade to concrete modules. **Canonical decision core:** `src/platform_core/`. **Windows portfolio / CLI:** `windows_network_toolkit/`.

## Phase 1 — Core architecture consolidation

| File | Action |
|------|--------|
| `src/platform_core/attribution/` | **New** — diagnostic-only proxy attribution |
| `src/platform_core/proof/` | **New** — direct vs proxied proof engine |
| `src/platform_core/timeline/` | **New** — incident timeline builder |
| `src/platform_core/remediation/` | **New** — policy-gated preview + rollback |
| `src/platform_core/serialization.py` | **New** — deterministic JSON hashing |
| `windows_network_toolkit/diagnostics/proxy/runner.py` | **New** — orchestrates modules (no duplicate CLI logic) |
| Root `platform_core/` | **Unchanged (shim)** — fleet/SRE legacy; migrate incrementally |

## Phase 2 — Evidence model

| File | Action |
|------|--------|
| `src/platform_core/evidence/record.py` | **New** — `TypedEvidenceRecord`, chain of custody, ordinal confidence |
| `src/platform_core/contracts.py` | Existing `EvidenceItem` / `EvidenceBundle` — bridge via `to_evidence_item()` |
| `tests/platform_core/evidence/test_evidence_record.py` | **New** |

## Phase 3 — Proxy attribution

| File | Action |
|------|--------|
| `src/platform_core/attribution/models.py` | Listener classifications + process snapshot |
| `src/platform_core/attribution/classifier.py` | `NO_PROXY` … `DEAD_PROXY_CONFIG` ladder |
| `src/platform_core/attribution/collector.py` | WinINET/WinHTTP/netstat/CIM read-only collection |
| `tests/platform_core/attribution/test_listener_classification.py` | **New** |

## Phase 4 — Proof engine

| File | Action |
|------|--------|
| `src/platform_core/proof/engine.py` | DNS, TCP, HTTP direct/system/explicit |
| `src/platform_core/proof/models.py` | `ProofOutcome` taxonomy |
| `tests/platform_core/proof/test_proof_engine.py` | **New** |

## Phase 5 — Incident timeline

| File | Action |
|------|--------|
| `src/platform_core/timeline/builder.py` | Normalizes proxy, probe, remediation, audit |
| `tests/platform_core/timeline/test_timeline_builder.py` | **New** |

## Phase 6 — Policy-gated remediation

| File | Action |
|------|--------|
| `src/platform_core/remediation/planner.py` | Preview + approval token + policy gate |
| `src/platform_core/remediation/rollback.py` | Rollback plan before execution |
| `tests/platform_core/remediation/test_remediation_planner.py` | **New** |

## Phase 7 — Audit-ready report

| File | Action |
|------|--------|
| `windows_network_toolkit/audit/report_generator.py` | **Extended** — `generate_erp_report()` |
| `tests/fixtures/erp/sample_audit_report.json` | **New** sample fixture |

## Phase 8 — CLI

| Command | Module |
|---------|--------|
| `proxy-status` | `run_proxy_status` |
| `proxy-attribution` | `run_proxy_attribution` |
| `proxy-proof --url` | `run_proxy_proof` |
| `proxy-timeline [--url]` | `run_proxy_timeline` |
| `bad-gateway-diagnose --url` | existing bad_gateway runner |
| `report [--url] [fixture]` | `generate_erp_report` / fixture replay |

## Phase 9 — Tests

See `tests/platform_core/**` and `windows_network_toolkit/tests/test_proxy_cli.py`.

## Phase 10 — Documentation

| File | Action |
|------|--------|
| `README.md` | Positioning, architecture, safety, commands, case study |
| `docs/IMPLEMENTATION_PLAN_ERP.md` | This file |

## Safety invariants (all phases)

- No silent registry mutation
- No process kill / firewall reset / adapter disable
- `dry_run=True` default
- Typed confirmation token required for execution
- Audit append before/after execution paths
- Rollback plan generated before destructive preview
