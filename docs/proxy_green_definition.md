# Proxy “green” definition (WinINET / localhost)

Operator and automation surfaces should use this definition before declaring an endpoint **green** after proxy remediation.

## Green criteria (all required)

1. **ProxyEnable** = `0` (HKCU WinINET).
2. **ProxyServer** absent or empty (value deleted or unset).
3. **AutoConfigURL** absent or empty (value deleted or unset).
4. **No active localhost proxy listener** on the previously configured port (optional live check via `python -m src proxy-owner`).
5. **No OFF→ON re-enable** during the configured **soak window** (default recommendation: 15 minutes).

## Not sufficient alone

- `ProxyEnable = 0` while **ProxyServer** still contains `127.0.0.1:<port>` (**LATENT_MISCONFIG**).
- Point-in-time verification immediately after `reg` writes (writer may re-enable minutes later).
- CPU process names in monitor logs (correlation only, not registry writer proof).

## Soak command

```powershell
python -m src proxy-disable --dry-run false --confirm DISABLE_WININET_PROXY --soak-minutes 15
```

Outcomes:

- **STABLE** — no re-enable during soak.
- **REMEDIATION_NOT_STICKY** — ProxyEnable returned to `1`; suspected **ACTIVE_REVERTER**; do not loop `reset_proxy.bat`.

## Canonical audit

Watch for flip-flops in `reports/proxy_guard_watch.jsonl` (see `docs/proxy_guard.md` for legacy mirrors).
