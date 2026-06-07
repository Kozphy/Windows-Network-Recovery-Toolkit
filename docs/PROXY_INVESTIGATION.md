# Proxy investigation (`proxy-investigate`) — Upgrade 1

Read-only **Level 1 correlation mode**. No Sysmon, Procmon, Event Log, or ETW required.

## Commands

```powershell
python -m src proxy-investigate
python -m src proxy-investigate --json
python -m src proxy-investigate --audit
python -m src proxy-investigate --no-audit
```

Default: read-only, no audit write.

## What it reports

| Section | Content |
| --- | --- |
| WinINET | ProxyEnable, ProxyServer, AutoConfigURL, ProxyOverride, parsed mode, localhost host/port |
| WinHTTP | Direct vs proxy; note if unavailable |
| Port owner | PID, name, parent, path, command line, start time when available |
| Correlation | Listener port match, process class, parent hints, proof_status |
| Evidence | **OBSERVED** / **CORRELATED** / **NOT PROVEN** (grouped) |
| Risk | Category, level, confidence, recommended policy action |
| Next steps | Existing safe commands (`proxy-stop-listener`, `proxy-stop-reverter`, `proxy-disable`, `proxy-watch`) |

## Risk categories

`NO_PROXY`, `MANUAL_LOCALHOST_PROXY`, `KNOWN_DEV_PROXY`, `KNOWN_SECURITY_TOOL`, `UNKNOWN_LOCAL_PROXY`, `SUSPICIOUS_LOCAL_PROXY`, `POSSIBLE_MITM_RISK`, `HIGH_RISK_PROXY_TRANSITION`, `REMEDIATION_NOT_STICKY`

Active **node.exe under powershell.exe** on the proxy port → typically `HIGH_RISK_PROXY_TRANSITION` (Level 1).

## Epistemic rules

- Listener on proxy port ≠ registry writer proof
- High risk ≠ malware
- Cursor.exe low-confidence attribution is never proven without event evidence
- **NOT PROVEN** always includes registry writer, malware, and Cursor causation disclaimers

## Fix path for your proxy-watch pattern (uses existing tools)

```powershell
# Admin one-shot
.\scripts\run_proxy_recovery_admin.ps1

# Or manual chain
python -m src proxy-stop-reverter --dry-run false --confirm STOP_PROXY_REVERTER
python -m src proxy-stop-listener --dry-run false --confirm STOP_PROXY_LISTENER
python -m src proxy-disable --dry-run false --confirm DISABLE_WININET_PROXY --soak-minutes 15
python -m src proxy-watch --interval 5
```

## Planned (Upgrade 2+)

- `proxy-stop-preview` / `proxy-stop` (exact PID, `STOP_LOCAL_PROXY_PROCESS`)
- `proxy-preview-fix` / `proxy-fix` aliases
- `proxy-soak` standalone command
- `docs/PROOF_ADAPTERS.md` (Level 2 optional proof)

## See also

- `docs/proxy_remediation_contract.md`
- `docs/epistemic_model.md`
