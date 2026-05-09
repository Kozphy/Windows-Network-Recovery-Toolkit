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

## Proxy writer attribution upgrade

The live Proxy Guard writer path adds `logs/proxy_writer_audit.jsonl` and the
`ProxyAttributionEvent` timeline model. It preserves the same evidence boundary:

| Event level | Source |
| --- | --- |
| `OBSERVED_STATE` | Current WinINET proxy tuple. |
| `STATE_CHANGE` | Before/after registry tuple diff. |
| `CORRELATED_PROCESS` | Listener/process correlation for a configured localhost proxy port. |
| `WRITER_PROOF` | Sysmon Event ID 13, Windows Security 4657, Procmon CSV, or ETW-style registry write telemetry. |

Netstat tells who is listening. Sysmon/Procmon tells who wrote the registry. These are different.

When telemetry is missing, reports must say:

`writer proof unavailable; enable Sysmon registry telemetry or import Procmon trace.`

The relevant commands are:

```powershell
python -m proxy_guard watch-writer
python -m proxy_guard writer-report --json
python -m proxy_guard writer-report --markdown
python -m proxy_guard import-procmon path\to\procmon.csv
python -m proxy_guard explain-event <event_id>
```

## `registry_writer_proof` contract

`evidence/registry_writer_proof.py` projects the rich evidence into a strict shape consumed by
the CLI (`python -m src proxy registry-writer-proof --json`) and the optional API
(`POST /api/proxy/registry-writer-proof`). The contract is intentionally narrow so dashboards
and audits can reason about availability without parsing per-source bundles:

```json
{
  "registry_writer_proof": {
    "status": "unavailable | found",
    "evidence_level": "observation | proof_candidate",
    "events": [
      {
        "timestamp": "...",
        "image": "...",
        "process_id": 4242,
        "user": "...",
        "target_object": "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Internet Settings\\ProxyServer",
        "value_name": "ProxyServer",
        "details": "127.0.0.1:57863",
        "event_source": "sysmon_event_13",
        "source_event_id": "13",
        "confidence": 0.94
      }
    ],
    "limitation": "listener/process correlation does not prove registry writer identity ...",
    "sysmon_status": {"installed": true, "running": true, "log_available": true}
  }
}
```

Boundaries enforced by the facade:

- The adapter is **read-only**. It never installs Sysmon, never elevates, never clears event logs, never kills processes.
- Permission errors and missing telemetry collapse into `status: "unavailable"` with a stable `reason` field; the CLI never crashes on a non-Sysmon host.
- `evidence_level` is `proof_candidate`, never `proof`. Operators must still review process identity, parent context, and signing before treating a row as authoritative.
- Listener / process correlation remains classified as `inference`; only registry-write telemetry is upgraded to `proof_candidate`.
