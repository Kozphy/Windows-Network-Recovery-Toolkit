# Case study 001: Proxy drift from Cursor / Node dev server

## Summary

A developer workstation enabled loopback proxy `127.0.0.1:64394` during an IDE session. WinINET settings changed without operator awareness. The platform detected drift, correlated listener ownership to `node.exe` parented by `Cursor.exe`, and gated remediation to **preview-only**.

## Outcome

- **Detection:** proxy-watch transition within 60s look-back
- **Classification:** `KNOWN_DEV_TOOL` (allowlist + process name)
- **Policy:** `OBSERVE` — log and timeline, no kill/disable
- **Proof:** Sysmon Event ID 13 fixture shows registry writer alignment (synthetic demo)

## Reproduce (read-only)

```powershell
python -m src proxy-timeline --fixture tests/fixtures/proxy_incidents/cursor_known_proxy.json --format markdown
python -m src incident-review --incident-id 001_proxy_drift_cursor_node --format markdown
```
