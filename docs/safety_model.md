# Safety Model

This project is designed for beginner users, so safety is more important than aggressive repair.

## Allowed by default (read-only)

- Read WinINET / WinHTTP registry and `netsh` excerpts  
- Run proxy health probes and path contrasts  
- Classify evidence and generate governance reports  
- Export CSV / Power BI star-schema tables  
- Verify audit hash chains and replay fixtures  

## Blocked by default

- Registry mutation without typed confirmation  
- Live `proxy-disable` apply without dry-run review  
- Process kill, firewall reset, adapter disable  
- Autonomous remediation narratives  
- Malware / MITM verdicts without limitations  
- AI-authorized execution  

## Required for sensitive actions

- Explicit command flag (`--dry-run` default false only with intent)  
- Typed confirmation token (`DISABLE_WININET_PROXY`, etc.)  
- Policy decision recorded in audit log  
- Limitation disclosure in output  

---

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

### Allowlisted state-changing actions

| `action_id` | Confirmation phrase | Allowed registry fields | Reversible |
| --- | --- | --- | --- |
| `disable_wininet_proxy` | `DISABLE_WININET_PROXY` | `ProxyEnable` (and optionally `ProxyServer` via `--clear-server`) | Yes (LKG snapshot) |
| `restore_wininet_proxy_from_lkg` | `RESTORE_WININET_PROXY_FROM_LKG` | `ProxyEnable`, `ProxyServer`, `AutoConfigURL`, `ProxyOverride`, `AutoDetect` | Yes (previous snapshot) |

### Permanently blocked actions

The following remain blocked from any CLI / API remediation path even with confirmation. They must be handled manually with operator-supervised tooling:

- `firewall_reset`
- `disable_adapter`
- `adapter_reset`
- `winsock_reset`
- `kill_process`
- `delete_certificate`
- `broad_registry_cleanup`
- `arbitrary_shell`

### Last Known Good (LKG) snapshot

Before a confirmed mutation, the toolkit captures HKCU WinINET state into `logs/proxy_snapshots.jsonl` (transient rollback) and named snapshots into `logs/proxy_known_good_snapshots.jsonl`. The `proxy restore-lkg` subcommand is the only path that may restore those WinINET fields and only via the typed phrase `RESTORE_WININET_PROXY_FROM_LKG`. WinHTTP, Git, npm, environment variables, browser policies, and any non-WinINET registry path are intentionally out of scope for this command.

### Post-change validation

After a confirmed mutation the CLI re-reads HKCU WinINET, runs DNS / TCP 443 / HTTPS direct probes, and writes a `post_change_validation` audit row. Validation failure never triggers broad automatic repair; it is surfaced as `repair_effect: unchanged | unknown` so the operator can decide.

### Agent next-step planner

`python -m src agent next-step` and `POST /platform/agent/next-step` only suggest the next read-only probe or preview action. The planner output always includes `policy_boundary: "recommendation_only_no_mutation"` and a `blocked_actions` list. The planner cannot execute remediation, change registry, kill processes, reset firewall, disable adapters, delete certificates, or run arbitrary shell. See `docs/agent_next_step.md`.

### LLM boundary

LLMs may translate structured evidence into prose. They may not invent observations, attribution, proof, or remediation. See `docs/event_state_reasoning_platform.md` for the full structured-only contract.

### What this toolkit is not

This is not antivirus, not autonomous containment, and not a replacement for endpoint detection and response. It is a local-first diagnostic, evidence, and confirmation-gated remediation-preview toolkit.
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

## WNT JSON CLI enforcement (tests)

Primary CLI: `python -m windows_network_toolkit`. Safety contracts are enforced in:

- `tests/windows_network_toolkit/test_safety_contract.py` — dry-run default, confirmation token, blocked actions
- `tests/windows_network_toolkit/test_cli_json_contract.py` — valid JSON on all commands
- `tests/windows_network_toolkit/test_audit_soft_fail.py` — audit write failure does not crash commands

Blocked by default: process kill, firewall reset, adapter disable, WinHTTP mutation. See [classification-model.md](classification-model.md) and [proof-vs-observation.md](proof-vs-observation.md).

