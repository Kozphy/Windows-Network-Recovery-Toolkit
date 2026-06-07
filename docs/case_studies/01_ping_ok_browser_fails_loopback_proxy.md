# Case study: Ping works, browser fails (loopback proxy path)

Fictional composite based on toolkit signals; no real hostnames or corporate data.

## Context

Windows 11 laptop. User reports Edge shows timeouts or proxy errors while `ping 8.8.8.8` succeeds. Dev tooling (Node/Electron) was used earlier the same day.

## Observed signals (facts)

| Signal | Value |
| --- | --- |
| `ping_ok` | true |
| `dns_ok` | true |
| `tcp443_ok` | true (transport probe) |
| `browser_https_failed` / app HTTPS | false |
| `wininet_proxy_enable` | 1 |
| `wininet_proxy_server` | `127.0.0.1:54321` |
| `winhttp_direct_access` | true (WinHTTP often still direct) |
| `listener_up` | true on port 54321 |
| `proxied_https_ok` | false |
| `bypass_https_ok` | true |
| Sysmon registry SetValue (proxy keys) | not found in search window |

## Hypotheses (ranked, not proven)

| Rank | Hypothesis | Confidence (ordinal) |
| --- | --- | --- |
| 1 | Browser path regression via broken localhost proxy | high |
| 2 | WinINET/WinHTTP split-stack misconfiguration | medium |
| 3 | Unrelated DNS outage | low (contradicted by `dns_ok`) |

**Competing explanation:** Another process may have enabled WinINET while `node.exe` only listens—listener correlation is not registry-writer proof.

## Evidence level

| Layer | Tier |
| --- | --- |
| Registry delta | observation (poll) |
| Listener `node.exe` PID | inference (correlation) |
| HTTPS contrast (proxied fail, bypass ok) | validated / proof for **path** only |

## Proof status

| Check | Status |
| --- | --- |
| Localhost proxy HTTPS contrast | **CONFIRMED** (path broken through proxy, direct bypass works) |
| Registry writer identity | **UNPROVEN** (no Sysmon 13 in window) |

## Policy decision

```json
{
  "decision": "PREVIEW",
  "reason_codes": [
    "HIGH_CONFIDENCE_UNPROVEN",
    "REQUIRES_OPERATOR_CONFIRMATION",
    "PREVIEW_UNTIL_PROOF",
    "REQUIRES_TYPED_CONFIRMATION"
  ],
  "blocked_actions": [
    "firewall_reset",
    "adapter_disable",
    "process_kill",
    "arbitrary_shell"
  ]
}
```

After operator runs proof workflow **and** types confirmation, safe-tier `restore_proxy` / `disable_proxy` may reach **ALLOW** in `platform_core.reasoning_engine`—still not automatic.

## Remediation preview (no auto-execute)

1. `python -m src proxy disable` (preview)  
2. When soak reports `REMEDIATION_NOT_STICKY`, preview reverter + listener stop:  
   `python -m src proxy-stop-reverter --dry-run`  
   `python -m src proxy-stop-listener --dry-run`  
3. Confirmed stop (Administrator PowerShell):  
   `python -m src proxy-stop-reverter --dry-run false --confirm STOP_PROXY_REVERTER`  
   `python -m src proxy-stop-listener --dry-run false --confirm STOP_PROXY_LISTENER`  
4. Confirmed disable + optional chained reverter/listener:  
   `python -m src proxy disable --dry-run false --confirm DISABLE_WININET_PROXY --stop-reverter-first --stop-reverter-confirm STOP_PROXY_REVERTER --stop-listener-first --stop-listener-confirm STOP_PROXY_LISTENER --soak-minutes 15`  
   Or run `.\scripts\run_proxy_recovery_admin.ps1` (re-launches elevated if needed).  
5. `python -m src proxy-status` and `python -m src proxy-path-status` for validation  

Reverter stop targets the attributed parent `powershell.exe` tree only — not registry-writer proof. Listener stop uses port attribution only.

## Final validation

| Check | Expected after fix |
| --- | --- |
| `ProxyEnable` | 0 or intentional known-good |
| `proxied_https_ok` / browser | success |
| `proxy-watch` JSONL | no repeat drift within soak window |

## Limitations

- Do not label `node.exe` as malware or confirmed registry writer.  
- `ping` success does not prove browser path health.  
- Proof confirms **path behavior**, not **intent** or **persistence**.  
- Re-enable risk if dev proxy keeps running—document soak failures in audit.

## Related commands

```powershell
python -m src diagnose --live
python -m src proxy-watch-report --tail 5
python -m src replay <run_id>
```
