# Case study 002: Browser fails, ping OK

## Summary

End-user reports HTTPS failures while `ping 8.8.8.8` succeeds — classic split-path symptom. Platform probes separate **L3 reachability** from **WinINET proxy path** and surfaces proxy drift as leading hypothesis without claiming proof.

## Outcome

- **Detection:** browser_path_failed signal with dns_ok / ping_ok
- **Evidence level:** observation + correlation (proxy enabled, external-looking PAC not required)
- **Policy:** `PREVIEW` remediation — reset proxy preview only, dry-run default

## Reproduce

```powershell
python -m src incident-review --incident-id 002_browser_fails_ping_ok --format markdown
```
