# Safety Model

This project is designed for beginner users, so safety is more important than aggressive repair.

## Safety Principles

- Diagnose before changing settings.
- Prefer targeted fixes over full reset.
- Ask before applying repairs.
- Require typed confirmation before any registry or network state mutation.
- Avoid actions that can disconnect the user unexpectedly.
- Keep firewall reset manual.
- Keep logs local.

## Read-Only Operations

These actions do not change network settings:

- Showing network adapters
- Running `ping`
- Running `nslookup`
- Running `Test-NetConnection`
- Running `curl`
- Showing WinHTTP proxy settings
- Reading user proxy registry values

`auto_diagnose.bat` only performs read-only operations.

## Repair Operations

These actions change settings:

- Flushing DNS cache
- Resetting Winsock
- Resetting TCP/IP
- Resetting WinHTTP proxy
- Updating user proxy registry values
- Resetting Windows Firewall

Repair scripts require Administrator permission.

## Preview vs Execute

Preview is read-only. It may read current WinINET, WinHTTP, DNS, TCP, HTTPS, listener, or LKG state and write an append-only audit row that a preview was requested.

Execute is any path that can change Windows state. Execute defaults to `dry_run=true`. A live mutation requires all of the following:

- `dry_run=false`
- known allowlisted `action_id`
- exact typed confirmation phrase
- mutation limited to the action's allowed fields
- append-only audit rows for request, block/success, and validation

For WinINET proxy disable, the allowlisted action is:

- `action_id`: `disable_wininet_proxy`
- required phrase: `DISABLE_WININET_PROXY`
- allowed registry field: `ProxyEnable`

For LKG proxy restore, the allowlisted action is:

- `action_id`: `restore_wininet_proxy_from_lkg`
- required phrase: `RESTORE_WININET_PROXY_FROM_LKG`
- allowed registry fields: `ProxyEnable`, `ProxyServer`, `AutoConfigURL`, `ProxyOverride`, `AutoDetect`

Safe proxy restoration only changes targeted HKCU WinINET fields. It does not reset WinHTTP, firewall, adapters, certificates, VPNs, browsers, or unrelated registry keys.

## Explicit Non-Goals

The toolkit does not:

- Disable network adapters
- Disable network adapter bindings
- Kill processes
- Delete certificates
- Run broad registry cleanup
- Remove VPN software
- Remove antivirus software
- Change router settings
- Change ISP settings
- Reset firewall automatically
- Bypass enterprise policies

## Restart Requirements

Some Windows network resets do not fully apply until reboot.

Restart after:

- `one_click_fix.bat`
- Any guided repair that runs `one_click_fix.bat`

## Managed Devices

Work or school computers may use policy-managed proxy, firewall, or VPN settings.

On managed devices:

- Ask IT before resetting proxy settings.
- Ask IT before resetting firewall settings.
- Expect some settings to return automatically after reboot or sign-in.

## Failure Knowledge System (`failure_system`)

The Failure Knowledge System adds structured **FailureBlocks** and **JSONL** storage. It **never**:

- Runs `.bat` repair scripts or elevated resets automatically.
- Invokes `netsh` repair verbs, Winsock resets, firewall resets, or adapter toggles from its Python API or CLI.

It **does**:

- Execute **read-only** probes (for example `ping`, `nslookup`, `curl`, `ipconfig`, `netsh winhttp show proxy`, `route print`).
- Emit **text** recommendations and persist records for **local** search.

Risk labels (`low` / `medium` / `high`) describe the **severity of the suggested manual action** if an operator chooses to follow guidance—not an automated enforcement level.

## Logs stay local

Unless **you** copy files or configure optional demo components yourself:

- Default posture is **no upload** of `logs/`, `reports/`, or `data/failure_blocks/*.jsonl` to external telemetry sinks.
- Treat JSONL and logs as **operator-private**; redact before sharing in public issues.

## Proxy Guard LKG rollback (Python CLI)

When `python -m src proxy-guard --auto-rollback` is enabled without `--dry-run` / `--dry-run-rollback`,
the loop may **replay `reports/proxy_guard_lkg.json`** into HKCU Internet Settings plus optional WinHTTP restores.
Treat this like any other remediation: reviewers must widen `trusted_exe_paths` / process allowlists only through PRs.

## Proxy writer attribution safety

`python -m proxy_guard watch-writer` is diagnose-first and append-only. It reads WinINET proxy
values, correlates listener candidates, queries registry-write telemetry when available, runs bounded
connectivity probes, and appends events to `logs/proxy_writer_audit.jsonl`.

It does not:

- Kill processes.
- Delete certificates.
- Reset firewall.
- Disable adapters.
- Restore or delete registry values automatically.

Policy gates are intentionally conservative:

- If writer proof is unavailable, the event is `PREVIEW` only.
- Listener correlation is `candidate_actor` only.
- Known writers allow safe restore preview only, not automatic registry mutation.
- Unknown writer plus localhost proxy plus suspicious certificate or persistence indicators blocks
  automatic remediation and recommends manual investigation.
- Any registry restore must be targeted and explicitly confirmed through a separate remediation path.

Netstat tells who is listening. Sysmon/Procmon tells who wrote the registry. These are different.

Heuristic attribution does not prove registry writer identity. Listener ownership can support a candidate hypothesis only; registry writer proof requires registry-write telemetry such as Sysmon Event ID 13 or imported Procmon-style data.

## Gitignore expectations / logging hygiene

Real operational artifacts should remain untracked:

- `logs/`, `reports/`, `data/failure_blocks/*.jsonl`, `*.log`, local `.env` files — see root `.gitignore`.
- **Do commit** `tests/fixtures/` and `examples/` fiction — **do not** paste production dumps there.

## Public-safe vs private data

| Public-safe (typical) | Keep private |
| --- | --- |
| Source code, tests, docs | Real `logs/` and `reports/` |
| `tests/fixtures/`, `examples/` samples | Live FailureBlock JSONL from your LAN |
| Synthetic FailureBlocks in docs | Hostnames, SSIDs, corporate domains |
| Architecture diagrams | Proxy endpoints, internal IPs, full `ipconfig` |
| | Truncated audit fingerprints if policy-sensitive |

When in doubt, **redact** before publishing.

## Evidence-backed attribution boundary (platform)

Structured **`/platform/attribution/*`** payloads explain *detect → correlate → classify evidence strength* but **never** elevate registry polling alone to forensic certainty. Offline demos preload **`platform_data/attribution_context.jsonl`** so Sysmon/Procmon extracts can be exercised without transmitting raw telemetry. High-risk remediation (firewall reset, opaque shell, arbitrary adapter disables) stays **blocked** from autonomous API paths—see **`docs/rbac_and_remediation.md`**.

