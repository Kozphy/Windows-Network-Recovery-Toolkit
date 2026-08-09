# Dead localhost WinINET proxy — 3-layer recovery

**Architecture (v0.3.0):** [startup-observability.md](startup-observability.md) — combined install, boot trace JSONL, evidence bundle, operator report.

## Problem

Windows **WinINET** (browser) proxy can point at a stale localhost port such as `127.0.0.1:62285` with `ProxyEnable=1` while **nothing is listening** on that port. Symptoms:

- Browsers fail with `ERR_PROXY_CONNECTION_FAILED`
- Ping and DNS often still work
- WinHTTP may still report direct access (stack mismatch)

This commonly happens when **Cursor**, **Node**, or other local dev proxy tools exit but leave HKCU proxy keys behind.

## What this solves

| Layer | Script | Role |
|-------|--------|------|
| **0. One-shot auto** | `scripts/auto-fix-proxy.ps1` or `python -m src auto-fix-proxy` | Cursor fix + live guardian + fallback proxy-fix + 60s background guardian |
| **0b. ChatGPT auto** | `scripts/auto-fix-chatgpt.ps1` | Proxy auto-fix + bad-gateway diagnose + ChatGPT scenario + LOW-risk remediations — see [chatgpt-auto-fix.md](chatgpt-auto-fix.md) |
| **1. Root cause** | `scripts/configure-cursor-no-proxy.ps1` | Stops Cursor from managing system proxy (`http.proxySupport: off`) |
| **2. Startup observability** | `scripts/install-startup-observability.ps1` or `python -m src install-startup-observability` | One preview-first install for guardian + boot trace with automatic Startup hook fallback if Task Scheduler is denied |
| **2a. Guardian only** | `scripts/install-dead-proxy-guardian.ps1` | Guardian-only install for operators who do not want boot trace |
| **2b. Boot trace only** | `scripts/install-proxy-boot-trace-task.ps1` | Boot-trace-only install for operators who do not want guardian |
| **3. Emergency button** | `scripts/fix-wininet-proxy.cmd` | One-click manual HKCU disable when the browser is broken right now |

### Guardian safety

`proxy-guardian` remediates:

| Case | Condition | Confirm token |
|------|-----------|---------------|
| **Dead** | enabled localhost proxy, **no listener** | `CLEAR_DEAD_LOCALHOST_PROXY` |
| **Active-but-broken** (opt-in `--clear-broken`) | listener up, proxy path probe failed | `PREFER_DIRECT_WININET` |
| **Hold-direct** (opt-in `--hold-direct`) | **any** enabled localhost WinINET (incl. healthy tunnels) | `PREFER_DIRECT_WININET` |

Background loop (`scripts/run-proxy-guardian-loop.ps1`) enables dead + broken + **hold-direct** at a **15s** interval, with a **PowerShell emergency fallback** if Python fails. After one install you should not need manual clears.

```powershell
# Set-and-forget (recommended)
.\enable-proxy-autofix.cmd
# Status heartbeat
Get-Content .\reports\proxy_guardian_heartbeat.json
# Uninstall
.\enable-proxy-autofix.cmd uninstall
```

Listener process name/cmdline is recorded in the audit as **correlation only** (not registry-writer proof).


### Active-but-broken (listener up, path failed)

When a process is listening on the configured localhost port but **HTTPS via the proxy fails** while **direct HTTPS works**, drift classification is **`BROKEN_LOCALHOST_PROXY`** (legacy: `DEAD_PROXY_CONFIG` for analytics).

| Surface | Behavior |
|---------|----------|
| `auto-fix-proxy` / `ensure-proxy-health` | Detects via proxy-vs-direct path probe; clears with confirm `PREFER_DIRECT_WININET` (same token as prefer-direct). Without confirm → `needs_prefer_direct_confirm` / `localhost_proxy_broken`. |
| `proxy-guardian --clear-broken` | Broken/unusable path clear in the loop. |
| `proxy-guardian --hold-direct` | Clears **any** enabled localhost WinINET (recurrence / prefer-direct policy). |
| Healthy active localhost (no hold-direct) | Left alone unless `--prefer-direct` on ensure/auto-fix. |

```powershell
# LinkedIn / browser timeout — one shot (Python optional)
.\fix-linkedin-proxy.cmd
.\scripts\fix-linkedin-proxy.ps1

# Emergency clear (no Python)
.\scripts\emergency-clear-wininet-proxy.ps1 -Force
.\scripts\fix-wininet-proxy.cmd /Y

# Clear active-but-broken (or force direct for healthy active)
.\scripts\auto-fix-proxy.ps1 -PreferDirect
python -m src auto-fix-proxy --prefer-direct --confirm PREFER_DIRECT_WININET --json
python -m src proxy-guardian --once --clear-broken --hold-direct --confirm-broken PREFER_DIRECT_WININET --dry-run false --json
# Install 15s auto-clear loop (hold-direct on)
.\scripts\install-dead-proxy-guardian.ps1 -IntervalSeconds 15
```

### Recurring rewrite with suspicious persistence (operator containment)

Hold-direct **clears** WinINET but does **not** remove a Session-0 scheduled task / `system32` payload that keeps rewriting (example pattern: task actions with `iex (iwr …)` + `Add-MpPreference` exclusions + `VersionUpdater*` under `%WINDIR%\System32`).

Use the one-command containment path (**no AI prompt required**):

```powershell
# Preview (default)
.\contain-localhost-rewriter.cmd
python -m src contain-localhost-rewriter --json

# Live apply (elevated; typed token CONTAIN_LOCALHOST_REWRITER)
.\contain-localhost-rewriter.cmd /APPLY
python -m src contain-localhost-rewriter --confirm CONTAIN_LOCALHOST_REWRITER --dry-run false --json
```

| Step | Behavior |
|------|----------|
| Detect | Heuristic match on remote-iex tasks, Defender exclusion tasks, `system32\<non-OS>\node.exe` / `VersionUpdater*` |
| Preview | Default — planned task delete / process stop / exclusion remove / quarantine |
| Apply | Requires confirm `CONTAIN_LOCALHOST_REWRITER` (or `/APPLY` on the `.cmd`) |
| After | Keep `enable-proxy-autofix.cmd` / hold-direct until `logs\proxy_guardian.jsonl` shows no further `guardian_hold_direct_apply` |

**Boundaries:** Not malware attribution; not registry-writer proof; does not weaken `KILL_PROXY_PROCESS` in `safety.py` (this is a distinct operator-gated composite). WNRT guardian / boot-trace tasks and `\Microsoft\Windows\*` tasks are never targeted. Audit: `logs/rewriter_containment.jsonl`. Quarantine: `reports/quarantine/`.

### Broken IPv6 + healthy IPv4 (YouTube / Edge stall)

When WinINET is direct but browsers spin on YouTube/Google while `curl -4` works and `curl -6` returns `http_code=000`, classify with **network-path-health**:

```powershell
python -m src network-path-health --json
.\fix-network-path.cmd
.\fix-network-path.cmd /APPLY
.\fix-youtube.cmd
```

| Case | Meaning | Action |
|------|---------|--------|
| `IPV6_BROKEN_IPV4_OK` | IPv4 probes OK, IPv6 fail | Prefer-IPv4 + disable Wi-Fi IPv6 (`PREFER_IPV4_OVER_IPV6`) |
| `IPV6_BROKEN_MITIGATED` | Mitigation already on; default path OK | Browser: `fix-youtube.cmd` (`--disable-quic`) |
| `PROXY_ENABLED_CHECK_GUARDIAN` | ProxyEnable=1 | Use guardian / contain first |

Confirm token: `PREFER_IPV4_OVER_IPV6`. Audit: `logs/network_path_health.jsonl`.

### ChatGPT auto-fix safety (layer 0b)

[auto-fix-chatgpt.ps1](chatgpt-auto-fix.md) chains layer 0 with ChatGPT scenario diagnosis and **LOW-risk only** remediations:

| Boundary | Enforcement |
|----------|-------------|
| Proxy HKCU mutation | Step 1 uses `DISABLE_WININET_PROXY` via `proxy-guardian` — same dead-proxy rules as layer 0 |
| ChatGPT LOW-risk apply | Step 4 requires `APPLY_CHATGPT_LOW_RISK` for live `flush_dns`, `reset_winhttp_proxy`, `restart_chatgpt_app` |
| MEDIUM/BLOCK tier | Firewall reset, disable firewall, process kill — **never** auto-executed |
| Session/cache | App restart is a low-risk test; **no** automated cache or cookie clear |
| Malware / writer proof | Does not claim attack, malware, or registry writer identity |
| Server-side outage | HTTPS probes may fail externally; auto-fix does not prove OpenAI availability |

If messages stay blank after a clean proxy path, follow manual recovery in [chatgpt-auto-fix.md](chatgpt-auto-fix.md#recovery-steps).

## What this does not solve

- Corporate VPN or mandatory enterprise proxy (do not disable without policy approval)
- WinHTTP-only or per-app proxy settings (Git, npm, `HTTP_PROXY` env vars) — see `scripts/proxy_guard/reset_proxy_safe.ps1` for broader cleanup
- Proof of who wrote the registry key (listener correlation is not writer proof)
- Malware or MITM — this is endpoint reliability triage, not EDR
- **Silent** process kill via the agent/policy path (`KILL_PROXY_PROCESS` stays blocked). Operator containment of matched rewriter persistence is opt-in via `contain-localhost-rewriter` + `CONTAIN_LOCALHOST_REWRITER`.

## Install (no admin required)

**Fastest — automatic fix (recommended):**

```powershell
.\scripts\auto-fix-proxy.ps1
python -m src auto-fix-proxy
.\scripts\auto-fix-chatgpt.ps1
```

Recommended startup-time install from the repository root:

```powershell
.\scripts\install-startup-observability.ps1
.\scripts\install-startup-observability.ps1 -Apply
python -m src install-startup-observability --json
```

This preview-first installer attempts a per-user Scheduled Task for each component and, if Task Scheduler returns `Access is denied`, automatically falls back to:

- `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\WNRT-DeadProxyGuardian.cmd`
- `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\WNRT-ProxyBootTrace.cmd`

Step-by-step alternatives:

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

Optional component-specific startup-time evidence collection (read-only):

```powershell
.\scripts\install-proxy-boot-trace-task.ps1
.\scripts\install-proxy-boot-trace-task.ps1 -Apply
```

This installs `WNRT-ProxyBootTrace`, which runs:

```powershell
python -m src proxy-boot-trace --duration 180 --interval 2
```

30 seconds after logon so VPN, Cursor, and other startup tools have time to touch WinINET before the trace begins.

You can verify the preferred or fallback install path with:

```powershell
schtasks /Query /TN WNRT-DeadProxyGuardian
schtasks /Query /TN WNRT-ProxyBootTrace
dir "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\WNRT-*.cmd"
```

Evidence collection and summary:

```powershell
python -m src collect-evidence-bundle
python -m src startup-observability-report --json
```

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
.\scripts\install-startup-observability.ps1 -Uninstall
.\scripts\install-startup-observability.ps1 -Uninstall -Apply
python -m src uninstall-startup-observability --dry-run false --confirm UNINSTALL_STARTUP_OBSERVABILITY
```

This removes scheduled tasks and Startup hooks if present. The operation is idempotent, so it still succeeds if only one install method exists.

## Related CLI

```powershell
python -m windows_network_toolkit proxy-status
python -m windows_network_toolkit diagnose
python -m windows_network_toolkit proxy-disable --dry-run false --confirm DISABLE_WININET_PROXY
```
