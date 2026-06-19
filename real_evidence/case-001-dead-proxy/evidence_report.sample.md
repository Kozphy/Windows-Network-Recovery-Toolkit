# Evidence Report — Case 001 Dead Localhost Proxy

**SAMPLE — sanitized portfolio evidence**

## Executive summary

Endpoint reliability triage indicates a dead WinINET localhost proxy configuration. Browser traffic is routed to `127.0.0.1:59081` but the proxy path does not succeed. Direct HTTPS path works. This is management information for technology risk review — not a formal audit opinion.

## Classification

- **Incident class:** `DEAD_PROXY_CONFIG`
- **Secondary signals:** `WININET_WINHTTP_MISMATCH`
- **Policy decision:** `PREVIEW_ONLY`

## Evidence

1. WinINET ProxyEnable = 1, ProxyServer = 127.0.0.1:59081
2. No TCP listener on port 59081
3. Direct HTTPS probe: success
4. Proxy HTTPS probe: failure (connection refused)

## Recommended action

Preview `proxy-disable` with dry-run default. Live apply requires typed confirmation `DISABLE_WININET_PROXY`.

## Limitations

- Does not prove malware
- Does not prove MITM
- Listener/process attribution is correlation only without registry writer proof
- Classification is not accusation
