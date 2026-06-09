# Bad Gateway / 502 Diagnostic

Read-only diagnostic for proxy vs upstream failures.

## Command

```powershell
python -m windows_network_toolkit bad-gateway-diagnose --url https://example.com/api
python -m toolkit bad-gateway-diagnose --url https://example.com/api
```

## Pipeline integration

DNS → TCP → HTTP (system proxy) → HTTP (direct) → evidence tier → hypothesis → policy → audit

## Cause codes

| Code | Meaning |
|------|---------|
| `LOCAL_PROXY_MISCONFIG` | Proxy enabled; split-path suggests local misconfig |
| `LOCAL_LOOPBACK_PROXY` | 127.0.0.1 listener correlated (not writer proof) |
| `VPN_SECURITY_PROXY` | Enterprise/VPN proxy hints |
| `DNS_TCP_CONNECTIVITY_ISSUE` | DNS or TCP failure |
| `REMOTE_UPSTREAM_FAILURE` | 502 on both proxy and direct paths |
| `INCONCLUSIVE` | Insufficient signal |

## Safety

- No registry mutation
- No process kill
- No firewall reset
- No automatic proxy changes

See [safety_doctrine.md](safety_doctrine.md).
