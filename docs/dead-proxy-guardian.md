# Dead localhost WinINET proxy — 3-layer recovery

## Problem

Windows **WinINET** (browser) proxy can point at a stale localhost port such as `127.0.0.1:62285` with `ProxyEnable=1` while **nothing is listening** on that port. Symptoms:

- Browsers fail with `ERR_PROXY_CONNECTION_FAILED`
- Ping and DNS often still work
- WinHTTP may still report direct access (stack mismatch)

This commonly happens when **Cursor**, **Node**, or other local dev proxy tools exit but leave HKCU proxy keys behind.

## What this solves

| Layer | Script | Role |
|-------|--------|------|
| **0. One-shot auto** | `scripts/auto-fix-proxy.ps1` | Cursor fix + live guardian apply + 1-minute background guardian |
| **0b. ChatGPT auto** | `scripts/auto-fix-chatgpt.ps1` | Proxy auto-fix + bad-gateway diagnose + ChatGPT scenario + LOW-risk remediations |
| **1. Root cause** | `scripts/configure-cursor-no-proxy.ps1` | Stops Cursor from managing system proxy (`http.proxySupport: off`) |
| **2. Startup guardian** | `scripts/install-dead-proxy-guardian.ps1` | At logon, runs a background loop every 5 minutes that clears **dead** proxy only |
| **3. Emergency button** | `scripts/fix-wininet-proxy.cmd` | One-click manual HKCU disable when the browser is broken right now |

### Guardian safety

`proxy-guardian` only remediates when classification is **`DEAD_PROXY_CONFIG`** (enabled localhost proxy, **no listener**). It does **not** clear an active localhost dev proxy while a process is still bound to the port.

## What this does not solve

- Corporate VPN or mandatory enterprise proxy (do not disable without policy approval)
- WinHTTP-only or per-app proxy settings (Git, npm, `HTTP_PROXY` env vars) — see `scripts/proxy_guard/reset_proxy_safe.ps1` for broader cleanup
- Proof of who wrote the registry key (listener correlation is not writer proof)
- Malware or MITM — this is endpoint reliability triage, not EDR

## Install (no admin required)

**Fastest — automatic fix (recommended):**

```powershell
.\scripts\auto-fix-proxy.ps1
.\scripts\auto-fix-chatgpt.ps1
```

Or step by step from the repository root:

```powershell
.\scripts\configure-cursor-no-proxy.ps1
.\scripts\install-dead-proxy-guardian.ps1
```

Restart **Cursor** after step 1. The guardian installs a Startup hook:

`%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\WNRT-DeadProxyGuardian.cmd`

Optional Task Scheduler (may require elevation or fail on locked-down PCs):

```powershell
.\scripts\install-dead-proxy-guardian.ps1 -UseScheduledTask
```

If registration is denied, you will see:

`Task Scheduler: skipped (access denied or policy block; startup hook is active)`

## Test

```powershell
& ".\.venv\Scripts\python.exe" -m windows_network_toolkit proxy-guardian --once
```

Expected when healthy: `"classification": "NO_PROXY"`, `"action_taken": "none"`.

Dry-run preview when dead proxy is present:

```powershell
python -m windows_network_toolkit proxy-guardian --dry-run true
```

## Emergency (manual)

Double-click or run:

```powershell
.\scripts\fix-wininet-proxy.cmd
```

Sets `ProxyEnable=0` and removes `ProxyServer` under HKCU. Use only when you need immediate browser relief.

## Uninstall guardian

```powershell
.\scripts\install-dead-proxy-guardian.ps1 -Uninstall
```

Removes the Startup hook, stops the background loop, and attempts to remove scheduled tasks if present.

## Related CLI

```powershell
python -m windows_network_toolkit proxy-status
python -m windows_network_toolkit diagnose
python -m windows_network_toolkit proxy-disable --dry-run false --confirm DISABLE_WININET_PROXY
```
