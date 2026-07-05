# ChatGPT auto-fix — connectivity and blank messages

One-shot orchestration for **ChatGPT desktop app / browser path degradation** when the root cause is likely local network configuration (dead proxy, DNS, WinHTTP drift, app restart). Chains the dead-proxy recovery layer with read-only diagnosis and **policy-gated LOW-risk remediations**.

**Related:** [dead-proxy-guardian.md](dead-proxy-guardian.md) (proxy layer only) · `src/network_recovery/` (scenario engine)

---

## When to use

| Symptom | May help | Will not fix |
|---------|----------|--------------|
| Browser or app cannot reach `chatgpt.com` | Dead localhost WinINET proxy, WinHTTP loopback hints, DNS cache | OpenAI server outage |
| Sidebar loads, messages blank | Proxy/VPN interaction, Electron stack, DNS | Session/cache corruption (restart is a test, not a cure) |
| `ERR_PROXY_CONNECTION_FAILED` | Step 1 proxy auto-fix | Corporate mandatory proxy (do not disable without policy) |

This is **endpoint reliability triage**, not malware detection, EDR, or proof of who wrote registry keys.

---

## Flow

```mermaid
flowchart TD
    START([Operator: auto-fix-chatgpt.ps1 or make fix-chatgpt]) --> S1{Skip proxy auto-fix?}

    S1 -->|No| P1[Step 1: auto-fix-proxy.ps1]
    P1 --> P1a[configure-cursor-no-proxy]
    P1a --> P1b[proxy-guardian --once]
    P1b --> P1c{DEAD_PROXY_CONFIG?}
    P1c -->|Yes| P1d["proxy-disable (DISABLE_WININET_PROXY)"]
    P1c -->|No| P1e[No HKCU mutation]
    P1d --> P1f[Optional: install 1-min guardian]
    P1e --> P1f
    P1f --> S2

    S1 -->|Yes| S2[Step 2: bad-gateway-diagnose — read-only]
    S2 --> S3[Step 3: src diagnose --app chatgpt — read-only]
    S3 --> S4[Step 4: auto-fix-chatgpt CLI]

    S4 --> S4a[Scenario diagnosis + signal collection]
    S4a --> S4b{Evidence selects LOW actions?}
    S4b -->|Live run| S4c["Confirmation gate (APPLY_CHATGPT_LOW_RISK)"]
    S4c --> S4d["flush_dns · reset_winhttp_proxy · restart_chatgpt_app"]
    S4b -->|Dry-run| S4e[Preview only — no mutations]
    S4d --> S5[Post-check HTTPS probes]
    S4e --> END2[Dry-run complete]
    S5 --> END{chatgpt_https_ok or outcome healthy?}
    END -->|Yes| OK[Exit 0 — retest browser/app]
    END -->|No| REC[Manual recovery — see below]
```

Steps 2–3 in the PowerShell script are **read-only**. Step 4 re-runs scenario diagnosis inside the CLI orchestrator (`src/network_recovery/auto_fix.py`) and applies LOW-risk actions when evidence-gated.

---

## Commands

### Recommended (no prompts)

```powershell
.\scripts\auto-fix-chatgpt.ps1
```

Or from the repository root:

```powershell
make fix-chatgpt
```

### Dry-run (preview only)

```powershell
.\scripts\auto-fix-chatgpt.ps1 -DryRun
```

```powershell
python -m windows_network_toolkit auto-fix-chatgpt --dry-run true
```

### Skip proxy layer (diagnosis + LOW-risk only)

```powershell
.\scripts\auto-fix-chatgpt.ps1 -SkipProxyAutoFix
```

### CLI only (step 4 — after proxy fix or for scripting)

```powershell
python -m windows_network_toolkit auto-fix-chatgpt --url https://chatgpt.com
python -m windows_network_toolkit auto-fix-chatgpt --dry-run true
python -m windows_network_toolkit auto-fix-chatgpt --skip-proxy-auto-fix --confirm APPLY_CHATGPT_LOW_RISK
```

Legacy read-only scenario diagnose (step 3 of the script):

```powershell
python -m src diagnose --app chatgpt --json
```

Manual MEDIUM-tier preview (never auto-applied):

```powershell
python -m src preview --scenario chatgpt_app_firewall
python -m src remediate --scenario chatgpt_app_firewall --dry-run false --confirm APPLY_CHATGPT_LOW_RISK
```

---

## Confirmation tokens

| Token | Used by | Mutations |
|-------|---------|-----------|
| `DISABLE_WININET_PROXY` | `proxy-guardian` / `proxy-disable` (step 1) | HKCU WinINET `ProxyEnable` (+ optional `ProxyServer` clear) when classification is `DEAD_PROXY_CONFIG` and **no listener** on the configured localhost port |
| `APPLY_CHATGPT_LOW_RISK` | `auto-fix-chatgpt` CLI / LOW-risk executor (step 4) | Allowlisted only: `ipconfig /flushdns`, `netsh winhttp reset proxy`, ChatGPT.exe stop/start |

Live apply uses the default token when `--confirm` is omitted (same posture as `proxy-disable`). `DEMO_MODE` forces dry-run across the toolkit.

---

## LOW-risk actions (evidence-gated)

| Action | Command | Notes |
|--------|---------|-------|
| `flush_dns` | `ipconfig /flushdns` | Selected when DNS probe fails or browser OK but app path fails |
| `reset_winhttp_proxy` | `netsh winhttp reset proxy` | WinHTTP loopback hints or proxy/localhost hypothesis |
| `restart_chatgpt_app` | Stop/start `ChatGPT.exe` | App process detected with degraded HTTPS probe |

**Never auto-executed:** firewall disable/reset, WFP filter deletion, arbitrary process kill, certificate deletion (`remediation_catalog.py` BLOCK/MEDIUM tiers).

---

## Audit paths

After a live run, review:

| Path | Contents |
|------|----------|
| `logs/network_recovery_events.jsonl` | Append-only scenario diagnosis + remediation rows |
| `reports/last_network_recovery_diagnosis.json` | Latest signal bundle, hypotheses, recommended actions |
| `.audit/proxy-disable.jsonl` | Guardian/proxy-disable apply rows (step 1) |
| `logs/proxy_snapshots.jsonl` | Pre-mutation snapshot when proxy-disable runs |

Override audit directory: `WNT_AUDIT_DIR` (default `.audit`).

---

## Limits (what this does not fix)

- **Session or site cache corruption** — hypotheses may rank `app_cache_or_session_issue`, but there is no automated cache clear; app restart is a low-risk test only.
- **Server-side OpenAI outages** — HTTPS probes may fail for external reasons; check status separately.
- **Firewall filtering (MEDIUM tier)** — `firewall_reset_preview` and stale rule cleanup are **preview-only**; requires manual review via `src preview`.
- **Malware / MITM / surveillance** — no verdicts; listener correlation is not registry-writer proof.
- **Active localhost dev proxy** — guardian will **not** clear proxy while a process listens on the configured port.

---

## Recovery steps

If JSON output shows degraded outcome or messages are still blank:

1. **Retest** in a private/incognito window or sign out/in at `chatgpt.com`.
2. **Clear site data** for `chatgpt.com` in browser settings.
3. **Review audit JSON** — `logs/network_recovery_events.jsonl` and `reports/last_network_recovery_diagnosis.json`.
4. **Proxy still dead?** Run `.\scripts\fix-wininet-proxy.cmd` or preview:
   ```powershell
   python -m windows_network_toolkit proxy-disable --dry-run
   python -m windows_network_toolkit proxy-disable --dry-run false --confirm DISABLE_WININET_PROXY
   ```
5. **Firewall hypothesis?** Manual preview only:
   ```powershell
   python -m src preview --scenario chatgpt_app_firewall
   ```

Exit codes: script **0** when HTTPS probe healthy or dry-run; **1** when still degraded.

---

## Privileges and idempotency

- **No admin** required for most steps (`ipconfig /flushdns` is user scope).
- Diagnosis steps are read-only and safe to repeat.
- LOW-risk commands are generally idempotent; app restart is disruptive but bounded to `ChatGPT.exe`.

---

## Module map

| Path | Role |
|------|------|
| `scripts/auto-fix-chatgpt.ps1` | Four-step PowerShell orchestrator |
| `src/network_recovery/auto_fix.py` | CLI orchestrator |
| `src/network_recovery/remediation_executor.py` | LOW-risk allowlist + `APPLY_CHATGPT_LOW_RISK` gate |
| `src/network_recovery/scenarios/chatgpt_app_firewall.py` | Hypothesis ranking |
| `windows_network_toolkit/cli.py` | `auto-fix-chatgpt`, `bad-gateway-diagnose` subcommands |

Tests: `tests/test_network_recovery_auto_fix.py`, `tests/test_network_recovery_chatgpt_scenario.py`
