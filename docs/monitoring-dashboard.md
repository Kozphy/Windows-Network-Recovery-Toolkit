# Local monitoring dashboard

Read-only NiceGUI dashboard for WinINET proxy evidence, classification, proof tier, and an audit timeline. Observation and classification only — remediation stays on policy-gated CLI commands.

## Usage

```powershell
pip install -e ".[dashboard]"
$env:PYTHONPATH = (Get-Location).Path
python -m windows_network_toolkit dashboard
# Open http://127.0.0.1:8765

python -m windows_network_toolkit procmon-import .\capture.csv
```

Useful flags:

| Flag | Meaning |
|------|---------|
| `--host` / `--port` | Bind address (default `127.0.0.1:8765`) |
| `--watch-interval` | Proxy poll seconds (default `1.0`, min `0.2`) |
| `--storage-path` | Explicit JSONL path (default `.audit/dashboard-events.jsonl`) |
| `--allow-non-loopback-bind` | Required to bind `0.0.0.0` / `::` (exposure risk) |

## Architecture

| Layer | Path | Role |
|-------|------|------|
| CLI | `windows_network_toolkit/cli.py` (`dashboard`, `procmon-import`) | Entry + bind safety |
| UI | `windows_network_toolkit/dashboard/` | NiceGUI Overview / timeline / process snapshot |
| Collectors | `collectors/proxy_state.py`, `proxy_listener.py`, `proxy_watcher.py`, `process_snapshot.py`, `procmon_import.py` | Read-only evidence |
| Storage | `storage/events.py`, `storage/event_store.py` | Schema + ring buffer + JSONL |
| Classification | Existing `proxy_classification` + `resolve_proof_tier` | No second engine |

Pipeline: **HKCU read → listener correlate → classify → append event (on change) → UI refresh**.

## Safety boundaries

- Binds to **127.0.0.1** by default (not `0.0.0.0`).
- No UI actions to disable proxy, write registry, terminate processes, or delete evidence files.
- **Clear UI view** hides rows in the ring buffer filter only; JSONL remains append-only.
- Pause/Resume stop/start the watcher thread only.
- Process / listener identity is **correlation**, not registry-writer or intent proof.

## Troubleshooting

| Symptom | Check |
|---------|--------|
| `SystemExit` / nicegui missing | `pip install -e ".[dashboard]"` |
| Refuses `0.0.0.0` | Use `127.0.0.1` or `--allow-non-loopback-bind` knowingly |
| Empty timeline | Wait for first poll (baseline) or import Procmon CSV |
| Classification `UNKNOWN` | Inspect event `limitations[]`; engines soft-fail |

## Audit notes

- Evidence file: `.audit/dashboard-events.jsonl` (or `--storage-path`).
- Each watcher change and Procmon import appends one JSON object per line.
- Do not truncate JSONL to “reset” the UI — use Clear UI view instead.
- Misread risk: listener PID next to ProxyServer ≠ proof of who wrote HKCU without Procmon/Sysmon writer evidence.

## Related

- [dead-proxy-guardian.md](dead-proxy-guardian.md)
- [procmon_proxy_filter.md](procmon_proxy_filter.md) (when present on branch)
- [code-documentation-standards.md](code-documentation-standards.md)
