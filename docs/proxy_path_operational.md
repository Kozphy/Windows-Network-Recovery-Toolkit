# Proxy path operational assessment

## Problem

The same WinINET registry signal can yield different browser outcomes:

| Case | ProxyEnable | Listener | Browser |
|------|-------------|----------|---------|
| A (broken) | 1 | localhost:PORT stale / dead | ERR_PROXY_CONNECTION_FAILED |
| B (healthy) | 1 | localhost:PORT + process alive | Works |

**Observation:** `ProxyEnable=1` is not sufficient to infer browser failure.

**Inference:** Failure requires a **non-operational proxy path** (wrong host, no listener, broken chain).

**Proof:** Requires **contrast checks** (proxied HTTPS vs `--noproxy` bypass), not registry alone.

## Composite states

| State | Meaning |
|-------|---------|
| `DIRECT` | Proxy off; no latent loopback server string |
| `LATENT_MISCONFIG` | `ProxyServer` set (often loopback) while `ProxyEnable=0` |
| `LOOPBACK_OPERATIONAL` | Proxy on, listener up, proxied path succeeds (or listener-only tier) |
| `LOOPBACK_BROKEN` | Proxy on, dead listener and/or proxied fails while bypass succeeds |
| `ENTERPRISE_PAC` | `AutoConfigURL` present (PAC drives routing) |

## Operational signals

- `listener_up` — netstat LISTEN on parsed localhost port
- `proxied_https_ok` — `curl -x http://127.0.0.1:PORT` (when loopback active)
- `bypass_https_ok` — `curl --noproxy '*'`
- `browser_path_healthy` — derived from composite + contrast (not a separate probe)

## Policy hints (operator layer)

| Composite | Operator hint |
|-----------|----------------|
| `LOOPBACK_OPERATIONAL` | `observe_no_rollback` — path works; guard does not auto-reset |
| `LOOPBACK_BROKEN` | `remediation_preview` — use `proxy-disable` preview before apply |
| Others | `observe_no_rollback` unless insufficient signal |

Internal JSONL still stores `allowed` / `blocked` / `observe`; human reports map these to operator vocabulary.

## Epistemic chain

`Observation → Event → State → Hypothesis → Evidence tier → Policy → Audit → Human text`

Do **not** claim malware, MITM, or hijack without an appropriate evidence tier.

Do **not** state that any process **caused** a registry change without **RegistryWriterProof** (Sysmon EID 13 / Procmon).

Listener correlation is **ListenerCorrelation**, not writer proof.

## CLI

```powershell
python -m src proxy-path-status
python -m src proxy-path-status --json
python -m src proxy-path-status --no-https-contrast
```

Proxy Guard runs the full assessment (including contrast) on each registry change event and attaches `proxy_path_operational` to `policy_decision` in audit JSONL.

## Module

`src/proxy_guard/proxy_path_operational.py` — `assess_proxy_path_operational()`, `classify_composite_state()`.
