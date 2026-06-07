# CLI reference

Long-form command inventory for `**python -m src**`, **proxy / network-state**, **endpoint agent**, **Failure Knowledge System**, and platform helpers. Beginner `**.bat`** flows stay in `[script_reference.md](script_reference.md)`.

## Purpose

Centralizes copy/paste commands referenced by the root `[README.md](../README.md)` so the README stays a short landing page for interviews.

## Safety boundaries

- Commands may invoke **local probes** (subprocess, registry reads, HTTP checks). None of the snippets here imply **silent repair**—guided repairs remain in `**scripts/*.bat`** with explicit prompts where implemented.
- Platform snippets assume **localhost** FastAPI and optional `**PLATFORM_DATA_DIR`**—do not point demos at production hosts without reviewing RBAC headers documented in `[platform_api_contract.md](platform_api_contract.md)`.

## Audit notes for reviewers

- Proxy attribution CLIs record honest telemetry tiers—correlate CLI JSON with append-only logs under `**logs/**` and `**platform_data/**` when demonstrating decisions.
- Reliability `**schema_version: "2.0"**` events under `**logs/snapshots.jsonl**`, `**repairs.jsonl**`, `**verifications.jsonl**`, `**drifts.jsonl**`, `**attribution.jsonl**`, `**incidents.jsonl**` complement legacy rows; see `[event_model_v2.md](event_model_v2.md)`.
- CI executes `**pytest**` only; destructive Windows batch files are **not** invoked by automated tests (see `[test_strategy.md](test_strategy.md)`).

## `python -m src` global option

Put `**--repo-root`** **before** the subcommand (argparse parses it on the root parser):

```powershell
python -m src --repo-root D:\checkout diagnose
```

Wrong: ~~`python -m src diagnose --repo-root D:\checkout`~~ (unrecognized).

## `python -m src` platform and prerequisites

Implementation reference: `**exit_code_if_not_windows**` / `**platform.system()**` in `[src/command_handlers.py](../src/command_handlers.py)`, `[src/cli.py](../src/cli.py)`, `[src/network_state/cli_handlers.py](../src/network_state/cli_handlers.py)`, `[src/proxy_guard/proxy_snapshot_commands.py](../src/proxy_guard/proxy_snapshot_commands.py)`.


| Subcommand                                                                                                                                           | OS                                                                        | Prerequisites / notes                                                                                                                     |
| ---------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| **diagnose**                                                                                                                                         | **Windows**, unless `**--fixture <features.json>`**                       | Without fixture uses `reg`, netsh, PowerShell probes. Fixture mode is CI/off-Windows friendly.                                            |
| **explain**                                                                                                                                          | Any                                                                       | `**reports/last_diagnosis.json`** from `**diagnose**`. Or `**--live**` + `**reports/last_diagnosis_live.json**` from `**diagnose-live**`. |
| **recommend**                                                                                                                                        | Any                                                                       | Same as **explain**.                                                                                                                      |
| **repair-safe**                                                                                                                                      | Preview: any (**needs artifacts** below). `**--apply`**: **Windows only** | Default: `**last_diagnosis.json`**. `**--live**`: `**last_diagnosis_live.json**`.                                                         |
| **repair-preview**                                                                                                                                   | Any                                                                       | Loads `**last_diagnosis_live.json`** if present, else `**last_diagnosis.json**` (`**diagnose-live**` / `**diagnose**`).                   |
| **repair-apply**                                                                                                                                     | **Windows**                                                               | Same artifact rule as **repair-preview**. May elevate via PowerShell (`Start-Process -Verb RunAs`).                                       |
| **feedback**                                                                                                                                         | Any                                                                       | Writes `**logs/decision_feedback.jsonl`**.                                                                                                |
| **export-report**                                                                                                                                    | Any                                                                       | `**last_diagnosis.json`**, or `**--live**` + `**last_diagnosis_live.json**`.                                                              |
| **diagnose-live**                                                                                                                                    | **Windows**                                                               | Live snapshot + v2 hypotheses; writes `**reports/last_diagnosis_live.json`**.                                                             |
| **snapshot**                                                                                                                                         | **Windows**                                                               | Full `**LiveNetworkSnapshot`** under `**reports/snapshots/**`.                                                                            |
| **proxy-status**, **proxy-owner**, **proxy-investigate**, **proxy-monitor**, **proxy-watch**, **proxy-guard**, **proxy-diagnose**, **proxy-attribution**, **proxy-disable** | **Windows**                                                               | HKCU WinINET / `reg` / netstat-style probes. (`**proxy-guard`** is guarded before `**--show-lkg**` too.)                                  |
| **proxy-report**                                                                                                                                     | Any                                                                       | Reads `**logs/proxy_guard.jsonl`** under repo root.                                                                                       |
| **proxy-rollback**                                                                                                                                   | **Windows**                                                               | `**--snapshot-id`** or `**--from-snapshot**` per help; typed confirm for destructive paths.                                               |
| **proxy-snapshot save**, **diff**, **restore**                                                                                                       | **Windows**                                                               | Live capture/compare/restore of allowlisted surfaces.                                                                                     |
| **proxy-snapshot list**, **show**                                                                                                                    | Any                                                                       | Read `**logs/proxy_known_good_snapshots.jsonl`** (and related paths).                                                                     |
| **network-state snapshot save**                                                                                                                      | **Windows**                                                               | Live capture path.                                                                                                                        |
| **network-state snapshot list**, **show**, **set-default**                                                                                           | Any                                                                       | Baseline metadata / JSONL only.                                                                                                           |
| **network-state diff**                                                                                                                               | **Windows**                                                               | Compares live machine to saved profile.                                                                                                   |
| **network-state report**                                                                                                                             | Any (see notes)                                                           | Aggregates JSONL events; `**drift_vs_default`** may be `**capture_unavailable**` if `**capture_proxy_snapshot**` fails off-Windows.       |
| **network-state restore**                                                                                                                            | **Windows**                                                               | Gated confirmations; previews without live apply unless confirm phrase matches.                                                           |
| **network-state evidence import**                                                                                                                    | Any                                                                       | Appends `**logs/network_state_evidence.jsonl`** from CSV.                                                                                 |


**Exit semantics (typical):** non-Windows guarded commands exit `**2`** with a stderr line; missing diagnosis files exit `**1**` or raise a handled `**FileNotFoundError**` (`**explain`/`recommend`/`repair-safe`/`export-report**` print a hint).

## Decision engine (`python -m src`)

```powershell
cd <repo-root>
python -m src diagnose
python -m src diagnose --fixture path\to\features.json
python -m src diagnose-live
python -m src snapshot
python -m src explain
python -m src explain --live
python -m src recommend
python -m src recommend --live
python -m src repair-safe
python -m src repair-safe --live
python -m src repair-preview
python -m src repair-apply
python -m src export-report
python -m src export-report --live
python -m src feedback --diagnosis-id <id> --recommended-action <what> --user-feedback-fixed <true|false|unknown>
```

## Proxy drift investigation (module API)

Read-only workflow — **no** `python -m src` subcommand yet. See [`proxy_investigation_workflow.md`](proxy_investigation_workflow.md).

```powershell
python -c "from pathlib import Path; from src.proxy_investigation import run_proxy_investigation; r = run_proxy_investigation(repo_root=Path('.')); print(r.run_id, r.primary_hypothesis_id)"
```

| Output | Path |
| --- | --- |
| JSONL audit | `logs/proxy_investigation.jsonl` |
| Markdown report | `reports/proxy_investigations/<run_id>.md` |

**Safety:** does not disable proxies or kill processes; remediation previews reference existing `proxy disable` CLIs below.

## Proxy observability and WinINET

```powershell
python -m src proxy-status
python -m src proxy-investigate
python -m src proxy-investigate --json
python -m src proxy-investigate --audit
python -m src proxy-diagnose
python -m src proxy-diagnose --json
python -m src proxy-attribution
python -m src proxy-watch --interval 5
python -m src proxy-report
python -m src proxy disable
python -m src proxy disable --dry-run
python -m src proxy disable --dry-run false
python -m src proxy disable --dry-run false --confirm DISABLE_WININET_PROXY
python -m src proxy-disable --dry-run
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

**Safety:** Listener and process correlation are **not cryptographic proof** of who wrote registry values. `**proxy disable**` and legacy `**proxy-disable**` default to dry-run preview. Live HKCU mutation requires `**--dry-run false --confirm DISABLE_WININET_PROXY**`; the allowlisted disable action may change only `**ProxyEnable**`. Confirmed mutation appends `**logs/proxy_snapshots.jsonl**` before `reg` writes and appends `**logs/repair_audit.jsonl**` for preview, execute request, block/success, and post-change validation. See `[proxy_guard.md](proxy_guard.md)`, `[proxy_attribution.md](proxy_attribution.md)`.

Preview is not execute:

- `python -m src proxy disable --dry-run` previews only.
- `python -m src proxy disable` also previews only because dry-run is the default.
- `python -m src proxy disable --dry-run false` blocks without confirmation.
- `python -m src proxy disable --dry-run false --confirm DISABLE_WININET_PROXY` may execute the targeted allowlisted `ProxyEnable` change.

### Proxy Guard decision notes

- `proxy-guard` first evaluates policy, then can run post-change connectivity validation (DNS/TCP443/HTTPS).
- Localhost listener presence is a **provisional signal**, not proof of registry writer identity.
- Regression-aware outcomes include states like `allowed_no_regression` and `allowed_but_connectivity_regressed`.
- Rollback actions remain policy-gated and explicit (`rollback_preview` / applied paths) and are limited to proxy-relevant surfaces.

## Network State Manager

```powershell
python -m src network-state snapshot save --name home-clean
python -m src network-state snapshot set-default --name home-clean
python -m src network-state diff --default --json
python -m src network-state report --since 24h
python -m src network-state restore --name home-clean --dry-run
python -m src network-state evidence import --file evidence.csv
```

See `[network_state_manager.md](network_state_manager.md)`.

## Safety surfaces (`proxy restore-lkg`, `proxy config-check`, `proxy registry-writer-proof`, `agent next-step`)

These four subcommands round out the production-grade safety controls. All four default to read-only, audit every preview / block / execute, and follow the typed-confirmation gate for any mutation.

```powershell
# Preview-only WinINET LKG restore (default dry-run)
python -m src proxy restore-lkg

# Live restore, only allowed via the typed phrase and only for WinINET fields
python -m src proxy restore-lkg --dry-run false --confirm RESTORE_WININET_PROXY_FROM_LKG

# Read-only proxy config audit across WinINET, WinHTTP, Git, npm, env, browser policy
python -m src proxy config-check --json

# Read-only Sysmon / Security 4657 / Procmon CSV writer evidence
python -m src proxy registry-writer-proof --json
python -m src proxy registry-writer-proof --json --procmon-csv .\trace.csv --since-seconds 600

# Bounded local agent planner; never mutates
python -m src agent next-step --json
python -m src agent next-step --goal recommend_preview_action --json
python -m src agent next-step --run-id <diagnosis_id> --json
```

Audit rows for these surfaces are appended to `logs/safety_audit.jsonl`. The contract for the proxy restore / preview / block lifecycle is documented in [`proxy_remediation_contract.md`](proxy_remediation_contract.md). The agent planner contract is documented in [`agent_next_step.md`](agent_next_step.md).

## Failure Knowledge System

```powershell
pip install -r failure_system\requirements.txt
python -m failure_system diagnose
python -m failure_system diagnose --json
python -m failure_system diagnose --markdown
python -m failure_system diagnose --verbose
python -m failure_system search "dns"
python -m failure_system recommend --query "browser"
uvicorn failure_system.api:app --host 127.0.0.1 --port 8010
```

Output layering contract: [`failure_system_output_contract.md`](failure_system_output_contract.md).

### Layer-aware diagnosis and preview

```powershell
scripts\diagnose_layers.bat
scripts\repair_preview.bat
python -m failure_system.layer_decision
python -m failure_system.layer_decision --no-write
```

Artifacts:

- `logs/network_layer_audit.jsonl` (append-only diagnosis ledger)
- `reports/network_layer_diagnosis_<timestamp>.md` (human-readable run report)

Safety:

- This path is diagnose/preview only: no silent process kill, firewall reset, adapter disable, or registry mutation.

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

HTTP sync uses `**/platform/ingest/***` routes with exponential backoff retries.

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
