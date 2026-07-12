# Localhost web-app diagnose

Evidence-based diagnosis for browser errors such as:

```text
http://localhost:61161/ChtPopupForm
ERR_CONNECTION_REFUSED
localhost refused to connect
```

This toolkit records **observation → hypothesis → proof tier → policy preview**.  
It does **not** restart apps, change firewall rules, or disable the proxy by default.

## What ERR_CONNECTION_REFUSED usually means

The TCP handshake reached the local machine, but **no application accepted the connection** on that address/port. That is **not**, by itself, proof of:

- a firewall block
- proxy interference
- malware
- an attack

## Commands

```powershell
$env:PYTHONPATH = (Get-Location).Path

python -m windows_network_toolkit localhost-diagnose `
  --url "http://localhost:61161/ChtPopupForm" `
  --json --remediation-preview

python -m windows_network_toolkit localhost-diagnose `
  --host localhost --port 61161 --path /ChtPopupForm `
  --include-process --include-http --include-proxy-comparison `
  --include-nearby-listeners --verbose

python -m windows_network_toolkit localhost-watch `
  --url "http://localhost:61161/ChtPopupForm" `
  --interval 2 --duration 60 --jsonl-out localhost-watch.jsonl
```

## Decision tree

```text
Is the target loopback?
  → Does TCP connect? (probe 127.0.0.1 and ::1 separately)
    → Is a listener present on the port?
      → Is it bound to the correct address family (IPv4 vs IPv6 vs wildcard)?
        → Which process owns it? (correlation, not malice)
          → Does direct HTTP work?
            → Does proxy-aware HTTP differ?
              → Did the process restart or change ports? (needs prior/timeline evidence)
                → What proof tier is supported? (T0–T5)
```

## Classifications

| Code | Typical meaning |
|------|-----------------|
| `LOCALHOST_SERVICE_NOT_LISTENING` | Refused/no listener; no prior exit proof |
| `LOCALHOST_LISTENER_ACTIVE` | TCP + listener present |
| `LOCALHOST_IPV4_IPV6_BIND_MISMATCH` | One family connects; other refused |
| `LOCALHOST_PROCESS_EXITED_OR_RESTARTED` | Only with prior listener/timeline evidence |
| `LOCALHOST_PORT_CHANGED_POSSIBLE` | Nearby listeners — weak; do not overclaim |
| `LOCALHOST_PROXY_INTERFERENCE` | Direct OK, proxy-aware fails (preview only) |
| `LOCALHOST_HTTP_APPLICATION_ERROR` | TCP up; HTTP 4xx/5xx |
| `LOCALHOST_TIMEOUT` / `LOCALHOST_NAME_RESOLUTION_ERROR` / `LOCALHOST_ACCESS_DENIED` / `LOCALHOST_TRANSIENT_RACE` / `UNKNOWN_LOCALHOST_FAILURE` | As named |

## Safety

- Policy decision defaults to **PREVIEW**.
- Firewall changes and automatic proxy disable are **BLOCK**ed from this command.
- Service restart is proposed only when a service is deterministically identified; never fabricated.

See also: [proxy_health](../windows_network_toolkit/proxy_health.py), [procmon_proxy_filter.md](procmon_proxy_filter.md).
