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
| `heuristic` | Best-effort from polling + inventories only — cannot assert registry writer identity. |
| `listener_match` | Local listener ports align with `ProxyServer` text — correlation, **not proof** of the writer PID. |
| `procmon_confirmed` | Procmon **RegSetValue** CSV rows corroborate a writing process touching proxy keys — strong local evidence **if** exporters are trusted. |
| `sysmon_confirmed` | **Sysmon EID13** aligns with HKCU deltas — strongest *packaged* corroboration for this repo. |
| `etw_confirmed` | ETW-shaped stub fixtures hit keyword heuristics — intentionally **weaker** than Sysmon in claims. |

Legacy JSON may still say `evidence_supported` / `confirmed_by_eventlog`; use `evidence.models.coerce_attribution_level` to normalize.

Implementation: **`evidence/attribution_engine.py`** exposes **`build_attribution`**.

## Source modules

| Module | Responsibility |
| --- | --- |
| `registry_event_parser.py` | Parses before/after dicts into summaries (offline fixtures). |
| `sysmon_reader.py` | Normalizes Sysmon **EID13** projections. |
| `sysmon_eventlog.py` | Facade import path (re-exports `sysmon_reader`). |
| `procmon_importer.py` | Stdlib **`csv`** import of **RegSetValue** rows referencing proxy keys. |
| `procmon_csv.py` | Facade import path (re-exports `procmon_importer`). |
| `etw_reader.py` | **Stub/abstraction first** (`StubETWReader`). |
| `etw_stub.py` | Facade import path (re-exports `etw_reader`). |
| `evidence_event.py` | Normalized `EvidenceEvent` dataclass for correlation staging. |

## Platform bridge

Append optional context rows keyed by **`event_id`** via **`platform_data/attribution_context.jsonl`** (see **`platform_core.storage.append_attribution_context`**) before calling **`GET /platform/attribution/{event_id}`**. This keeps demos **offline** with embedded Sysmon CSV exports.

Correlate narrative flow with **`docs/proxy_attribution.md`** and **`docs/rbac_and_remediation.md`**.
