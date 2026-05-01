# Proxy Guard

Proxy Guard reads **HKCU** `Internet Settings` (`ProxyEnable`, `ProxyServer`, `AutoConfigURL`, `AutoDetect`), normalizes `ProxyServer` strings, correlates LISTENING `netstat` rows, optionally enriches via `Win32_Process` (through PowerShell/`Get-CimInstance`), emits JSONL audits, and offers a typed-phrase-guarded disable path (`DISABLE_PROXY`) that edits only WinINET user keys (**WinHTTP is intentionally untouched**).

## Commands

```powershell
python -m src proxy-status
python -m src proxy-status --json
python -m src proxy-owner [--port N] [--json]
python -m src proxy-monitor [--interval 5] [--once] [--jsonl logs/proxy_guard_events.jsonl]
python -m src proxy-disable [--dry-run] [--clear-server]
```

## Logs

Append-only sinks (local):

- `logs/proxy_guard_events.jsonl`
- `logs/repair_audit.jsonl` after successful `proxy-disable`

## Audit notes

Changing proxy disables the software that originally set the keys unless that software is addressed separately.
