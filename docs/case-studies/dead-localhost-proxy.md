# Case study: dead localhost WinINET proxy (127.0.0.1:59081)

**Classification:** `DEAD_PROXY_CONFIG` + secondary `WININET_WINHTTP_MISMATCH`  
**Proof status:** supported (confidence ~0.92)  
**Remediation allowed:** `DISABLE_WININET_PROXY` with typed confirmation only

---

## Symptom

- Ping and general ICMP reachability succeed.
- Browsers and WinINET-aware apps fail or hang on HTTPS.
- `curl` using WinHTTP may succeed while Chrome/Edge fail.
- LinkedIn, OAuth flows, and corporate SSO pages time out.

This pattern is common when **WinINET proxy is enabled** but the **configured localhost listener is dead**.

---

## Observation (golden fixture)

Fixture: `tests/fixtures/enert/dead_proxy_59081.json`

| Signal | Value |
|--------|-------|
| `ProxyEnable` | `1` |
| `ProxyServer` | `127.0.0.1:59081` |
| WinHTTP | direct (no proxy) |
| Listener on 59081 | **false** |

```powershell
python -m windows_network_toolkit proxy-status --fixture tests/fixtures/enert/dead_proxy_59081.json
```

---

## Classification

Primary: **`DEAD_PROXY_CONFIG`**

Secondary signals:

- `WININET_WINHTTP_MISMATCH` — browser path uses WinINET proxy; WinHTTP is direct
- `LOCALHOST_PROXY` — proxy server references loopback
- `DEAD_LOCALHOST_PORT` — netstat shows no listener

Severity: **medium** · Confidence: **0.92**

**Limitations (always surfaced):**

- Does not prove malware.
- Does not prove MITM.
- Does not identify which process originally wrote the registry key without Sysmon E13.

See [classification-model.md](../classification-model.md).

---

## Hypothesis

> Browser failure is likely caused by a dead WinINET localhost proxy.

WinINET-aware clients attempt to connect to `127.0.0.1:59081`. With no listener, connections fail while non-WinINET tools may still work.

---

## Proof envelope

```powershell
python -m windows_network_toolkit diagnose --proof --fixture tests/fixtures/enert/dead_proxy_59081.json
```

| Proof attempt | Status | Meaning |
|---------------|--------|---------|
| `localhost_listener_check` | failed | No process listening on configured port |
| `wininet_winhttp_comparison` | supported | Browser proxy path differs from WinHTTP direct path |

Conclusion: **supported** (confidence 0.92)

See [proof-vs-observation.md](../proof-vs-observation.md).

---

## Policy decision

| Action | Default |
|--------|---------|
| Observe / diagnose | Allow |
| `DISABLE_WININET_PROXY` | Allow **with** `--confirm DISABLE_WININET_PROXY` |
| Kill proxy process | **Blocked** (no listener exists) |
| WinHTTP mutation | **Blocked** |
| Firewall / adapter changes | **Blocked** |

```powershell
# Preview (default dry-run)
python -m windows_network_toolkit proxy-disable --dry-run

# Apply (WinINET HKCU only, audited)
python -m windows_network_toolkit proxy-disable --dry-run false --confirm DISABLE_WININET_PROXY
```

Audit trail: `.audit/proxy-disable.jsonl`

---

## Investigation follow-ups

1. **`proxy-watch`** — detect reverter respawn (`REVERTER_SUSPECTED`)
2. **`proxy-owner`** — when a listener appears, attribute PID/process
3. **`proxy-writer-attribution`** — Sysmon E13 registry writer proof (optional)
4. **`tls-proof`** — only if MITM indicators are present (not this case)

---

## Interview talking points

- Separated **observation** (registry + netstat) from **proof** (structured contrast checks).
- Chose **safe remediation** (WinINET disable) over destructive shortcuts.
- Documented **limitations** explicitly — no false "confirmed MITM" claims.
- Designed for **audit replay** — JSONL in `.audit/` merges into timeline and incident reports.

Related: [interview-case-study.md](../interview-case-study.md) · [three-minute-demo-script.md](../three-minute-demo-script.md)
