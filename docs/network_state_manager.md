# Network State Manager

Production-style **`snapshot → diff → attribution (heuristic) → policy → rollback preview → audit → report`** for Windows proxy stacks. This complements **`proxy-guard`** and **`proxy-snapshot`** with a dedicated artefact layout and event stream for future UI/tray tooling.

## Safety and privacy

- **No silent destructive repair.** Live restore requires the typed phrase **`RESTORE_NETWORK_STATE`** (unless you stay on implicit preview).
- **No firewall resets, adapter disable, or arbitrary shell.** Restores reuse argv-only **`reg` / `netsh` / `git` / `npm`** helpers from **`proxy_guard.rollback`** (same allowlisted surfaces as **`proxy-snapshot restore`**).
- **No mandatory Sysmon/Procmon.** Evidence import is optional CSV only.
- **No machine identifiers** in Network State artefacts beyond what proxy configuration strings already imply.
- **Attribution is heuristic** (`proxy-attribution` / listen-owner style data). Treat as investigative hint, **not proof** of who wrote registry values.

## Safe workflow

1. **Diagnose** — `python -m src proxy-diagnose` (and **`proxy-attribution`** if investigating loopback listeners).
2. **Save known-good** — While healthy:  
   `python -m src network-state snapshot save --name home-clean`
3. **Set default (optional)** —  
   `python -m src network-state snapshot set-default --name home-clean`  
   Writes **`config/network_state_default.json`**.
4. **Monitor** — **`proxy-guard`** with optional **`--known-good <name>`** (prefers **`logs/network_state_snapshots.jsonl`**, falls back to **`logs/proxy_known_good_snapshots.jsonl`**).
5. **Diff** —  
   `python -m src network-state diff --name home-clean [--json]` or **`diff --default`**
6. **Report** —  
   `python -m src network-state report --since 24h [--json]`  
   Writes **`reports/network_state_report.txt`** and **`reports/network_state_report.json`**.
7. **Restore preview** —  
   `python -m src network-state restore --name home-clean [--dry-run]`
8. **Confirm restore** —  
   `python -m src network-state restore --name home-clean --confirm RESTORE_NETWORK_STATE`

## CLI reference

Like other `python -m src` commands, **`--repo-root`** (when used) must appear **before** the subcommand, e.g. `python -m src --repo-root D:\sandbox network-state snapshot list`.

### Snapshots (`logs/network_state_snapshots.jsonl`)

| Command | Purpose |
| -------- | ------- |
| `network-state snapshot save --name <name>` | Capture WinINET (**ProxyEnable**, **ProxyServer**, **AutoConfigURL**, **ProxyOverride**), WinHTTP (`netsh` narrative), Git globals, npm **proxy** / **https-proxy**, user **HTTP_PROXY**, **HTTPS_PROXY**, **ALL_PROXY**, **NO_PROXY**. |
| `network-state snapshot list` | Profiles + **`is_default`**. |
| `network-state snapshot show --name <name>` | Latest JSON line for **`name`**. |
| `network-state snapshot set-default --name <name>` | Copy latest row to **`config/network_state_default.json`**. |

### Drift

`network-state diff --name <name> | --default [--json]`

Outputs **changed fields only** plus **suspicion flags** (e.g. proxy off→on, new loopback **`127.0.0.1:port`**, new PAC URL, Git/npm/env proxy appearing from empty).

### Policy (`config/network_state_policy.json`)

Copy **`shared/network_state_policy.example.json`** to **`config/network_state_policy.json`** and edit:

- **`allowed_process_names` / `blocked_process_names`** — matched against heuristic attribution **`owners[].process_name`** (lowercase).
- **`allowed_proxy_hosts` / `blocked_proxy_hosts`** — substring checks on parsed proxy host / raw **`ProxyServer`**.
- **`alert_on_unknown_loopback`** — add advisory reasons when loopback context is unknown.
- **`rollback_on_unknown_loopback`** — surface **`rollback_suggested`** in policy payload (executor remains **`proxy-guard`** / operator **`restore`**).

Missing file ⇒ **default-deny-soft** observe mode (see **`NetworkStatePolicy.default()`** in code).

### Report

Summarizes **`logs/network_state_events.jsonl`** in the **`--since`** window, default profile label, drift vs default (when **`config/network_state_default.json`** exists and live capture succeeds on Windows).

### Evidence import (optional)

`python -m src network-state evidence import --file <path.csv>`

Expects Procmon-like columns (**Path** / **Time of Day** / **Process Name** / **PID**, etc.). Rows touching **Internet Settings** registry paths append to **`logs/network_state_evidence.jsonl`**. Use **`match_evidence_to_drift_hint()`** in code for loose timestamp correlation — not automatic forensics.

### Restore

- **Default:** preview-only (no phrase) — two audit rows (**pre** / **post**) both reflect dry-run argv previews.
- **Live:** **`--confirm RESTORE_NETWORK_STATE`** and not **`--dry-run`**.

Audit: **`logs/network_state_audit.jsonl`**. Events: **`logs/network_state_events.jsonl`** (**`rollback_previewed`**, **`rollback_applied`**).

## Event hook types (`logs/network_state_events.jsonl`)

- **`snapshot_saved`**
- **`drift_detected`**
- **`policy_decision`**
- **`rollback_previewed`**
- **`rollback_applied`**
- **`evidence_imported`**
- **`report_generated`**

## Integration with `proxy-guard`

```powershell
python -m src proxy-guard --interval 5 --known-good home-clean --dry-run-rollback
python -m src proxy-guard --interval 5 --known-good home-clean --auto-rollback
```

**`--known-good`** resolves **`home-clean`** from **`logs/network_state_snapshots.jsonl`** first; if absent, from **`logs/proxy_known_good_snapshots.jsonl`**.

## Multi-profile mindset

Not every proxy is malicious — keep separate named profiles (**`home-clean`**, **`mobile-hotspot`**, **`vpn-work`**, **`dev-proxy`**) and compare with **`diff`** before restoring.

See also: **`docs/proxy_guard.md`**, **`docs/proxy_known_good_snapshot.md`**.
