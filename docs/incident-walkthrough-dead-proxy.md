# Incident walkthrough — dead localhost proxy

Step-by-step narrative moved from the root README. Fixture pack: [../fixtures/dead_proxy_config/](../fixtures/dead_proxy_config/).

## Narrative

Browser fails with `ERR_PROXY_CONNECTION_FAILED`. Ping and DNS work. WinINET shows proxy enabled toward `127.0.0.1:59081`. No listener on that port. WinHTTP is direct. Process owner unclear.

| Step | Action | Result |
|------|--------|--------|
| 1 | `proxy-status` | Structured WinINET/WinHTTP state |
| 2 | `proxy-owner` | Listener check; owner unknown or absent |
| 3 | `diagnose --proof` | Path contrast; proof envelope with limitations |
| 4 | Classifier | `DEAD_PROXY_CONFIG` (+ mismatch secondary) |
| 5 | Policy | `PREVIEW_ONLY` — no silent registry edit |
| 6 | `proxy-disable --dry-run` | Remediation preview only |
| 7 | Audit + report | JSONL row; governance markdown export |

One-page summary: [one-page-case-study-dead-proxy.md](one-page-case-study-dead-proxy.md)

---

## 3-layer recovery (Cursor / stale localhost proxy)

For recurring `ERR_PROXY_CONNECTION_FAILED` when WinINET points at a dead `127.0.0.1:PORT`:

```powershell
.\scripts\configure-cursor-no-proxy.ps1          # root cause — restart Cursor after
.\scripts\install-dead-proxy-guardian.ps1      # startup guardian (no admin)
.\scripts\fix-wininet-proxy.cmd                  # emergency manual reset
```

Full guide: [dead-proxy-guardian.md](dead-proxy-guardian.md)
