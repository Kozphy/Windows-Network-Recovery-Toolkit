# Case 001 — Dead Localhost WinINET Proxy

**SAMPLE — sanitized portfolio evidence.** No real hostnames, usernames, or machine paths.

## Case

Browser shows `ERR_PROXY_CONNECTION_FAILED` while ping and DNS still work.

## Evidence pattern

| Signal | Observed value |
|--------|----------------|
| WinINET ProxyEnable | `1` (enabled) |
| WinINET ProxyServer | `127.0.0.1:59081` |
| Listener on port | None OR proxy HTTPS probe fails |
| WinHTTP | Direct access enabled |
| Direct HTTPS path | Works |
| Proxy HTTPS path | Fails |

## Classification

- **Primary:** `DEAD_PROXY_CONFIG`
- **Secondary signals:** `WININET_WINHTTP_MISMATCH`, `LOCALHOST_PROXY`, `DEAD_LOCALHOST_PORT`
- **Proof tier:** T3–T4 when path/listener evidence is present; T1–T2 for registry observation alone

## Policy

- **Default:** `PREVIEW_ONLY` (dry-run)
- Registry mutation requires typed confirmation: `DISABLE_WININET_PROXY`
- No autonomous remediation

## Limitations

- Does not prove malware
- Does not prove MITM
- Listener/process attribution is correlation only unless registry writer evidence (Sysmon E13 / Procmon) exists
- Governance output is management information, not a formal audit opinion
- Confidence values are ordinal ranking weights, not calibrated probabilities

## Sample files

| File | Purpose |
|------|---------|
| `raw_proxy_status.sample.json` | Normalized proxy state snapshot |
| `wininet_registry_export.sample.txt` | Synthetic HKCU export excerpt |
| `winhttp_proxy.sample.txt` | WinHTTP direct-access excerpt |
| `netstat_snapshot.sample.txt` | No listener on configured port |
| `tls_direct_result.sample.json` | Direct path probe result |
| `tls_proxy_result.sample.json` | Proxy path probe result |
| `evidence_report.sample.md` | Management-information report |
| `audit.sample.jsonl` | Append-only audit rows (preview-only) |

## Related commands

```powershell
python -m windows_network_toolkit proxy-status --fixture tests/fixtures/enert/dead_proxy_59081.json
python -m windows_network_toolkit reviewer-demo --mode mixed
```
