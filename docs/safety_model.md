# Safety Model

This project is designed for beginner users, so safety is more important than aggressive repair.

## Safety Principles

- Diagnose before changing settings.
- Prefer targeted fixes over full reset.
- Ask before applying repairs.
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

## Explicit Non-Goals

The toolkit does not:

- Disable network adapters
- Disable network adapter bindings
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

## Gitignore expectations

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
