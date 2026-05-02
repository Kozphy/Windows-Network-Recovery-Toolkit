# CLI reference

Long-form command inventory for **`python -m src`**, **proxy / network-state**, **endpoint agent**, **Failure Knowledge System**, and platform helpers. Beginner **`.bat`** flows stay in [`script_reference.md`](script_reference.md).

## Decision engine (`python -m src`)

```powershell
cd <repo-root>
python -m src diagnose
python -m src explain
python -m src recommend
```

## Proxy observability and WinINET

```powershell
python -m src proxy-status
python -m src proxy-diagnose
python -m src proxy-diagnose --json
python -m src proxy-attribution
python -m src proxy-watch --interval 5
python -m src proxy-report
python -m src proxy-disable
python -m src proxy-rollback --snapshot-id ...
python -m src proxy-rollback --from-snapshot path\to\known_good.json --confirm RESTORE_PROXY_SNAPSHOT_FILE
python -m src proxy-monitor
python -m src proxy-guard --interval 5
python -m src proxy-guard --interval 5 --auto-rollback --trust-current
python -m src proxy-snapshot save --name my-baseline --as-default
python -m src proxy-snapshot list
python -m src proxy-snapshot show ...
python -m src proxy-snapshot diff ...
python -m src proxy-snapshot restore ...
python -m src proxy-guard --interval 5 --known-good my-baseline --dry-run-rollback
python -m src proxy-guard --interval 5 --known-good my-baseline --auto-rollback
```

**Safety:** Listener and process correlation are **not cryptographic proof** of who wrote registry values. **`proxy-disable`** appends **`logs/proxy_snapshots.jsonl`** before `reg` mutations. See [`proxy_guard.md`](proxy_guard.md), [`proxy_attribution.md`](proxy_attribution.md).

## Network State Manager

```powershell
python -m src network-state snapshot save --name home-clean
python -m src network-state snapshot set-default --name home-clean
python -m src network-state diff --default --json
python -m src network-state report --since 24h
python -m src network-state restore --name home-clean --dry-run
python -m src network-state evidence import --file evidence.csv
```

See [`network_state_manager.md`](network_state_manager.md).

## Failure Knowledge System

```powershell
pip install -r failure_system\requirements.txt
python -m failure_system diagnose
python -m failure_system search "dns"
python -m failure_system recommend --query "browser"
uvicorn failure_system.api:app --host 127.0.0.1 --port 8010
```

## Endpoint agent (observe-only)

```powershell
python -m endpoint_agent --once
python -m endpoint_agent.agent --once
python -m endpoint_agent --once --api http://127.0.0.1:8000
python -m endpoint_agent --loop --interval 30
python -m endpoint_agent --service --interval 30 --dry-run
```

Environment:

- `ENDPOINT_AGENT_API` — default base URL  
- `ENDPOINT_AGENT_DRY_RUN=1` — skip HTTP POSTs (local JSONL still written)  
- `PLATFORM_DATA_DIR` — JSONL root for `platform_core.storage`  

HTTP sync uses **`/platform/ingest/*`** routes with exponential backoff retries.

## Backend (FastAPI)

```powershell
$env:PYTHONPATH = (Get-Location).Path
pip install -r failure_system\requirements.txt
pip install -r requirements-platform.txt
uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

## Fake fleet demo (JSONL only)

```powershell
python -m platform_core.demo_fleet --data-dir platform_data_fleet_demo --reset
$env:PLATFORM_DATA_DIR = "$(Get-Location)\platform_data_fleet_demo"
```

Point the Next.js `NEXT_PUBLIC_PLATFORM_API` at a backend using the same `PLATFORM_DATA_DIR` for consistent metrics.

## Tests

```powershell
$env:PYTHONPATH = (Get-Location).Path
pytest -q
```
