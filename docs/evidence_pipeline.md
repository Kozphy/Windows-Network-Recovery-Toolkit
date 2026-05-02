# Evidence pipeline (`evidence/`)

This package models **observe-only** ingestion for **proxy and registry attribution** suitable for portfolios and auditors. Nothing here mutates HKCU/HKLM, firewall rules, adapters, or network routes.

## Honest attribution boundary

1. **Registry polling diffs** reveal *that* proxy keys changed—not *which OS process executed the registry write*.
2. **localhost listener correlation** narrows hypotheses (something is listening where `ProxyServer` points) but is still ambiguous when multiple tenants share tooling.
3. **Process inventory snapshots** expose *what is running contemporaneously*, not cryptographic proof of authorship.

Therefore the engine emits `attribution_level`:

| Level | Meaning |
| --- | --- |
| `unknown` | Insufficient observable context (rare; usually resolves to heuristic). |
| `heuristic` | Best-effort from polling + contemporaneous clues only — **explicitly weaker claims**. |
| `evidence_supported` | Structured telemetry (often Procmon/ETW-shaped) correlates a writer-like process — still reviewable. |
| `confirmed_by_eventlog` | **Sysmon Event ID 13** (registry value set to Internet Settings proxies) aligns with HKCU deltas — strongest *local* corroboration in this prototype without kernel ETW parity. |

Implementation: **`evidence/attribution_engine.py`** exposes **`build_attribution`**.

## Source modules

| Module | Responsibility |
| --- | --- |
| `registry_event_parser.py` | Parses before/after dicts into summaries (offline fixtures). |
| `sysmon_reader.py` | Normalizes Sysmon **EID13** projections. |
| `procmon_importer.py` | Stdlib **`csv`** import of **RegSetValue** rows referencing proxy keys. |
| `etw_reader.py` | **Stub/abstraction first** (`StubETWReader`) — preserves interface for eventual Windows ETW subscription wiring **without silently claiming kernel-level proof** in fixtures. |

## Platform bridge

Append optional context rows keyed by **`event_id`** via **`platform_data/attribution_context.jsonl`** (see **`platform_core.storage.append_attribution_context`**) before calling **`GET /platform/attribution/{event_id}`**. This keeps demos **offline** with embedded Sysmon CSV exports.

Correlate narrative flow with **`docs/proxy_attribution.md`** and **`docs/rbac_and_remediation.md`**.
