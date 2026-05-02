# Proxy Guard — attribution (best effort vs verified)

Polling `python -m src proxy-guard` reads HKCU Internet Settings snapshots on an interval.
That design **cannot**, by itself, prove **which process** mutated `ProxyEnable` / `ProxyServer`
between polls.

## Confidence ladder

| Source | Typical `confidence` field | Interpretation |
| --- | --- | --- |
| Sysmon Event ID 13 (+ readable Operational log) | `verified` / `verified_eventlog` | Treat as **verified registry writer attribution** once your parser positively correlates TargetObject/details for an Internet Settings proxy value. |
| Listen-port correlation + optional `psutil` | `medium` / `low` / `best_effort_process_snapshot` | **Heuristic** — good for triage, **not** court-grade proof. |
| No owners / no events | `unknown` | Default-deny policy should assume highest risk. |

## Modes

- `--attribution-mode auto` — try Sysmon JSON via PowerShell; else fall back to listen-owner heuristics.
- `--attribution-mode eventlog` — force Sysmon attempt; if logs are missing, emit limitations on the JSONL row and downgrade to best-effort.
- `--attribution-mode best-effort` — skip EventLog/Sysmon (`python -m src` path only; scripts under `scripts/proxy_guard/` remain unchanged).

## Engineering limitations

- **Security** / **Sysmon** logs may require elevation or role assignments; absence of events is not evidence of safety.
- Corporate hosts without Sysmon should rely on **MDM/SIEM exports** or enable **registry auditing** for HKCU if verifiable attribution is mandatory.

## Audit fields

Structured rows under `reports/proxy_guard_*.jsonl` and `logs/proxy_guard_audit.jsonl` include the full `AttributionResult` projection (`mode`, `confidence`, nested `process`, `evidence[]`, `limitations[]`).

