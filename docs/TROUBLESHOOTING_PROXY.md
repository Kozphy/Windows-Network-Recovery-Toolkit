# Proxy troubleshooting guide

Symptom-driven guide for **WinINET / WinHTTP proxy failures** on Windows. This is **endpoint reliability triage** — not malware detection, EDR, MITM confirmation, or autonomous remediation.

---

## Quick classification

| Observation | Likely label | Not this |
|-------------|--------------|----------|
| WinINET enabled → `127.0.0.1:PORT`, no listener | `DEAD_PROXY_CONFIG` | Malware verdict |
| WinHTTP direct, WinINET proxied | `WININET_WINHTTP_MISMATCH` | MITM proof |
| Proxy flips on/off without operator | `REVERTER_SUSPECTED` | Confirmed attacker |
| `git@github.com: Permission denied (publickey)` | SSH key config | Proxy failure |

---

## Incident pattern: dead localhost proxy (port 60505 example)

Documented live incident (2026-06-30):

| Signal | Value |
|--------|-------|
| WinINET `ProxyEnable` | `1` |
| WinINET `ProxyServer` | `127.0.0.1:60505` |
| Listener on 60505 | **None** (`SYN_SENT` only) |
| WinHTTP | Direct (OK) |
| TCP 443 to google.com | OK |
| HTTPS (WinINET-dependent apps) | **Failed** before fix |
| After `proxy-disable` + confirm | HTTPS **200 OK** |
| `git ls-remote` over HTTPS | OK after fix |
| `git@github.com` SSH | `Permission denied (publickey)` — **separate issue** |

Fixture: `tests/fixtures/enert/dead_proxy_60505.json`

---

## Step-by-step diagnosis

### 1. Snapshot (read-only)

```powershell
$env:PYTHONPATH = (Get-Location).Path
python -m windows_network_toolkit proxy-status
```

Check JSON:

- `classification` → expect `DEAD_PROXY_CONFIG` when localhost proxy is dead
- `diagnostic_hints` → WinHTTP split, SSH vs proxy, next commands
- `limitations` → must be present (observation ≠ proof)

### 2. Path probes (read-only)

```powershell
python -m windows_network_toolkit proxy-health --json
python -m windows_network_toolkit diagnose --proof
```

Compare **direct** vs **proxy** HTTPS probe results. Dead proxy often shows: direct OK, proxy path failed.

### 3. Listener correlation (read-only)

```powershell
python -m windows_network_toolkit proxy-owner
```

`listener_found: false` supports dead-port hypothesis — **correlation only**, not registry-writer proof.

### 4. Drift watch (read-only)

```powershell
python -m windows_network_toolkit proxy-watch --duration 300 --interval 2 --format human
python -m windows_network_toolkit dead-proxy-export
```

Audit: `.audit/proxy-watch.jsonl` (gitignored). Never commit real machine JSONL.

---

## Remediation (policy-gated)

### Preview first (default)

```powershell
python -m windows_network_toolkit proxy-disable --dry-run true
```

No registry mutation. Review `action_allowed`, `policy_reason`, rollback preview.

### Live apply (explicit confirmation)

```powershell
python -m windows_network_toolkit proxy-disable --dry-run false --confirm DISABLE_WININET_PROXY
```

Writes audit rows to `.audit/proxy-disable.jsonl`. **Recommendation is not execution authority** — operator must type the token.

### Guardian / one-shot scripts

```powershell
python -m windows_network_toolkit proxy-guardian --dry-run true   # preview
.\scripts\auto-fix-proxy.ps1                                     # live-by-default
```

`auto-fix-proxy.ps1` may apply with embedded confirmation — see [dead-proxy-guardian.md](dead-proxy-guardian.md).

---

## When classification says `NO_PROXY` but browsers still fail

Read `diagnostic_hints` on `proxy-status` output:

- Stale UI vs registry (re-run `proxy-status`)
- Per-app / IDE proxy (Cursor, Electron)
- VPN or corporate mandatory proxy
- DNS or TLS path issue (not WinINET dead proxy)
- **Git SSH errors are not proxy failures**

---

## Git: HTTPS vs SSH

### Verify HTTPS path (proxy-related)

```powershell
git remote -v
git ls-remote https://github.com/Kozphy/Windows-Network-Recovery-Toolkit.git
```

If HTTPS works, **network and WinINET path are likely restored** for tools using system proxy settings.

### SSH publickey errors (not proxy)

```
git@github.com: Permission denied (publickey)
```

| Fix | Command |
|-----|---------|
| Use HTTPS remote | `git remote set-url origin https://github.com/Kozphy/Windows-Network-Recovery-Toolkit.git` |
| Or fix SSH keys | Add public key in GitHub → Settings → SSH keys |

Do **not** run `proxy-disable` solely because SSH failed.

---

## Reverter / flapping proxy

If `proxy-watch` reports `REVERTER_SUSPECTED`:

1. `.\scripts\configure-cursor-no-proxy.ps1` — restart Cursor
2. Keep watch **read-only** — do not auto-kill processes
3. Preview only: `proxy-disable --dry-run true`

---

## Safety boundaries (always surface in reports)

1. Observation is not proof  
2. Correlation is not causation  
3. Classification is not accusation  
4. Confidence is ordinal, not probability  
5. Policy ALLOW is not a safety guarantee  
6. No malware / EDR / MITM verdict without independent proof  

---

## Related

- [WORKFLOW.md](WORKFLOW.md) — developer daily workflow  
- [dead-proxy-watch-workflow.md](dead-proxy-watch-workflow.md) — watch + export  
- [proxy_error.md](proxy_error.md) — `ERR_PROXY_CONNECTION_FAILED` (legacy bat scripts)  
- [incident-walkthrough-dead-proxy.md](incident-walkthrough-dead-proxy.md) — narrative walkthrough  
