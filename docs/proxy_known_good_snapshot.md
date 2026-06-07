# Last Known Good Network / Proxy Snapshot (`proxy-snapshot`)

Named, operator-captured snapshots of **allowlisted proxy-related network posture** (WinINET + WinHTTP + tool/env proxy layers) used to **compare** the current machine against a baseline and **restore** that baseline after drift or suspicious changes — without firewall resets, adapter disables, arbitrary shell pipelines, or log uploads.

## Data captured per `proxy-snapshot save`

| Surface | Fields / sources |
|--------|-------------------|
| **HKCU WinINET** | `ProxyEnable`, `ProxyServer`, `AutoConfigURL`, `ProxyOverride` (via registry probe shared with Proxy Guard). |
| **WinHTTP** | Full text of `netsh winhttp show proxy`, plus parsed direct-access vs proxy literal for restore. |
| **Git (global)** | `http.proxy`, `https.proxy`. |
| **npm (global)** | `proxy`, `https-proxy`. |
| **User environment (HKCU `Environment`)** | `HTTP_PROXY`, `HTTPS_PROXY`, `ALL_PROXY`, `NO_PROXY` (fallback reads lowercase variants when querying). |

Payloads intentionally avoid machine identifiers beyond what already appears inside proxy URLs you configure.

## Storage

| Path | Role |
|------|------|
| `logs/proxy_known_good_snapshots.jsonl` | Append-only stream; each line is `{ schema_version, name, saved_at, risk_summary, snapshot }`. Latest row per `--name` wins for `show`, `diff`, `restore`. |
| `config/last_known_good_proxy.example.json` | Committed synthetic template; copy locally to `config/last_known_good_proxy.json` (gitignored). |

## Operator workflow

**Diagnose → Save Known Good → Monitor → Diff → Restore** — use **`proxy-diagnose`** / batch diagnose first; capture **`proxy-snapshot save`** while healthy; **`proxy-monitor`** or **`proxy-guard`** for drift; **`proxy-snapshot diff`** before changing anything; **`proxy-snapshot restore`** only after review (typed confirm). For a fuller state/reporting pipeline, see **`docs/network_state_manager.md`** (**`network-state`**).

## CLI (`python -m src`, Windows only for capture/restore/diff live state)

```powershell
# After a verified-good network posture:
python -m src proxy-snapshot save --name work-home --as-default

# Inventory
python -m src proxy-snapshot list

# Inspect / compare
python -m src proxy-snapshot show --name work-home
python -m src proxy-snapshot diff --name work-home   # loopback anomalies flagged in JSON hints

# Restore (preview by default; live requires typed phrase)
python -m src proxy-snapshot restore --name work-home
python -m src proxy-snapshot restore --name work-home --confirm RESTORE_KNOWN_GOOD_PROXY
python -m src proxy-snapshot restore --name work-home --confirm RESTORE_KNOWN_GOOD_PROXY --dry-run   # stays preview-only
```

**Typed confirmation:** `RESTORE_KNOWN_GOOD_PROXY` — mistyped or omitted phrase ⇒ **dry-run only** (argv echoed, no HKCU/Git/npm/reg env writes). **`--dry-run`** forces preview even if the phrase matches.

Every restore attempt appends one JSON line to **`logs/proxy_guard_actions.jsonl`** with **`action=proxy_known_good_restore`**.

## `proxy-guard` integration

When monitoring detects a **blocked** transition and rollback is enabled, the default rollback target remains the **prior poll snapshot**. To rebuild from an explicit baseline instead:

```powershell
python -m src proxy-guard --interval 5 --known-good work-home --dry-run-rollback
python -m src proxy-guard --interval 5 --known-good work-home --auto-rollback
```

**`--known-good`** resolves the name from **`logs/network_state_snapshots.jsonl`** first (Network State Manager), then **`logs/proxy_known_good_snapshots.jsonl`** (`proxy-snapshot`). Rollback uses **`execute_known_good_proxy_restore`** (HKCU WinINET + WinHTTP + Git + npm + HKCU env proxy vars); **`--dry-run-rollback`** / **`--dry-run`** still inhibit live subprocesses.

## Safety and limitations

- **Argv-only subprocesses:** `reg.exe`, `netsh`, `git`, `npm` — **`shell=False` always**.
- **No firewall / NIC automation** from this module.
- **HKCU env restore** updates persistent user variables; **new shells** pick them up reliably; processes already running may retain old env until restart.
- **npm / git failures** (missing install, nonzero exit) surface as `"success": false` in JSON; review stderr fields in audits.
- **Never uploads** telemetry; all artifacts stay local under your repo/`--repo-root` tree.

## Tests

Deterministic offline tests live in **`tests/test_proxy_known_good.py`** — JSONL persistence, diff hints, **`capture_proxy_snapshot`** with injected registry (no HKCU probe), handler smoke with faked **`capture_proxy_snapshot`** / **`execute_known_good_proxy_restore`**, mocked dry-run restores, argv shape probes (**no registry writes**, no **`shell=True`**).
