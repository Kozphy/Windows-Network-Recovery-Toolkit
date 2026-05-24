# Site-specific browser timeouts (e.g. LinkedIn `ERR_TIMED_OUT`)

When **most sites work in Edge** but **one site** (LinkedIn, a bank portal, etc.) shows
`ERR_TIMED_OUT` or “Checking the proxy and the firewall”, treat it as a **layered**
problem: WinINET proxy state, path health, then browser/site-specific factors.

This guide uses only tooling and flows **present in this repository**.

## Decision tree

```text
Site fails in Edge
    │
    ├─ python -m src proxy-status → Proxy ON + 127.0.0.1:port?
    │       YES → proxy-path-status (expect LOOPBACK_BROKEN when listener dead)
    │             → stop dev proxy / node listener → proxy-disable + soak
    │
    └─ proxy-status OFF + proxy-path-status DIRECT + browser_path_healthy?
            YES → OS path OK at probe time → site/browser specific (below)
            NO  → diagnose-live + proxy-diagnose
```

## Toolkit commands (run while the site fails)

```powershell
cd <repo-root>

python -m src proxy-status
python -m src proxy-path-status
python -m src proxy-diagnose
python -m src proxy-watch-report --tail 5
```

| Signal | Interpretation |
| --- | --- |
| `LOOPBACK_BROKEN` | System proxy ON but localhost HTTPS path fails — browser timeouts common |
| `DIRECT` + `browser_path_healthy=True` | WinINET off at probe time — investigate Edge/DNS/site |
| `ACTIVE_REVERTER` in watch report | Intermittent ON/OFF — soak must be **STABLE** before calling fixed |
| `REMEDIATION_NOT_STICKY` after disable | Something re-enabled proxy during soak — stop reverter first |

## Contrast probe (outside CLI, same machine)

```powershell
curl.exe -4 -I --connect-timeout 15 https://www.linkedin.com/
curl.exe -4 -I --connect-timeout 15 https://www.google.com/
```

| Pattern | Next step |
| --- | --- |
| `curl` LinkedIn **200**, Edge **timeout** | Edge cache, extensions, Secure DNS, InPrivate test |
| Both **timeout** | `python -m src diagnose-live`; check DNS/VPN/firewall |
| `curl` fails only when `proxy-status` ON | Proxy reverter — see `docs/proxy_green_definition.md` |

## Edge-only mitigations (not registry mutation)

1. InPrivate window (no extensions) → retry the site.
2. Edge **Settings → Privacy → Security → Use secure DNS** → try Off temporarily.
3. Disable VPN/proxy extensions.
4. Clear site cookies/cache for the failing host.
5. Try another browser — if it works, WinINET remediation already succeeded.

## Audit artifacts

| Path | Use |
| --- | --- |
| `logs/repair_audit.jsonl` | `proxy_disable` + `proxy_disable_soak` rows |
| `reports/proxy_guard_watch.jsonl` | OFF→ON flip-flops and attribution |
| `reports/last_diagnosis_live.json` | Layer hypotheses from `diagnose-live` |

## Safety boundaries

- Do not loop `reset_proxy.bat` when soak reports `REMEDIATION_NOT_STICKY`.
- Listener correlation (`node.exe` on a port) is **not** registry-writer proof.
- This repo does not modify Edge profiles or site blocklists — only documents Windows proxy/path state.

## Related docs

- [proxy_green_definition.md](proxy_green_definition.md) — soak **STABLE** criteria
- [ping_ok_but_browser_fails.md](ping_ok_but_browser_fails.md) — L7 vs ICMP mismatch
- [case_studies/01_ping_ok_browser_fails_loopback_proxy.md](case_studies/01_ping_ok_browser_fails_loopback_proxy.md) — loopback proxy walkthrough
