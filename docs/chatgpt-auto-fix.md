# ChatGPT auto-fix — connectivity and blank messages

Preview-first orchestration for **ChatGPT desktop app / browser path degradation** when observations support local network configuration or cached Chromium transport-state hypotheses (dead proxy, DNS, WinHTTP drift, process fan-out, or `Network Persistent State`). It chains the dead-proxy layer with read-only diagnosis and **policy-gated LOW-risk remediations**.

**Related:** [dead-proxy-guardian.md](dead-proxy-guardian.md) (proxy layer only) · `src/network_recovery/` (scenario engine)

---

## When to use

| Symptom | May help | Will not fix |
|---------|----------|--------------|
| Browser or app cannot reach `chatgpt.com` | Dead localhost WinINET proxy, WinHTTP loopback hints, DNS cache | OpenAI server outage |
| Sidebar loads, messages blank | Proxy/VPN interaction, Electron stack, DNS, reversible Chromium network-state quarantine | Cookies, authentication/session corruption, server-side faults |
| Many `ChatGPT.exe` rows | Count and audit the exact rows; cold restart after confirmation | Prove that each process is hung or identify root cause from count alone |
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
    S4c --> S4d["flush_dns · reset_winhttp_proxy · restart or reversible network-state quarantine"]
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

### Recommended preview (default; no mutations)

```powershell
.\scripts\auto-fix-chatgpt.ps1
```

Or from the repository root:

```powershell
make fix-chatgpt
```

The script and CLI now default to dry-run. The preview reports the observed `ChatGPT.exe` count and bounded network-state file count. The current 50-process fan-out threshold is a heuristic review signal, not proof that any process is stuck.

### Confirmed apply

```powershell
.\scripts\auto-fix-chatgpt.ps1 -Apply -Confirm APPLY_CHATGPT_LOW_RISK
```

That command applies only the ChatGPT LOW-risk action; the proxy layer remains preview-only. To authorize both independently:

```powershell
.\scripts\auto-fix-chatgpt.ps1 -Apply -Confirm APPLY_CHATGPT_LOW_RISK -ProxyConfirm CLEAR_DEAD_LOCALHOST_PROXY
```

```powershell
python -m windows_network_toolkit auto-fix-chatgpt --dry-run false --confirm APPLY_CHATGPT_LOW_RISK
```

### Explicit dry-run

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
python -m windows_network_toolkit auto-fix-chatgpt --skip-proxy-auto-fix --dry-run false --confirm APPLY_CHATGPT_LOW_RISK
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
| `CLEAR_DEAD_LOCALHOST_PROXY` | `proxy-guardian` (step 1) | HKCU WinINET `ProxyEnable` when classification is dead/stale and **no listener** exists on the configured localhost port |
| `DISABLE_WININET_PROXY` | Standalone `proxy-disable` | Explicit standalone HKCU WinINET proxy-disable workflow |
| `APPLY_CHATGPT_LOW_RISK` | `auto-fix-chatgpt` CLI / LOW-risk executor (step 4) | Allowlisted only: `ipconfig /flushdns`, `netsh winhttp reset proxy`, bounded ChatGPT.exe stop/start, and reversible `Network Persistent State` quarantine when selected by evidence |

Tokens are never inferred or filled automatically. Live ChatGPT apply requires both `--dry-run false` and `APPLY_CHATGPT_LOW_RISK`; live proxy repair additionally requires `--proxy-confirm CLEAR_DEAD_LOCALHOST_PROXY`. `DEMO_MODE` forces dry-run across the toolkit.

---

## LOW-risk actions (evidence-gated)

| Action | Command | Notes |
|--------|---------|-------|
| `flush_dns` | `ipconfig /flushdns` | Selected when DNS probe fails or browser OK but app path fails |
| `reset_winhttp_proxy` | `netsh winhttp reset proxy` | WinHTTP loopback hints or proxy/localhost hypothesis |
| `restart_chatgpt_app` | Stop/start `ChatGPT.exe` | App process detected with degraded HTTPS probe |
| `cold_restart_chatgpt_network_state` | Stop ChatGPT, verify zero matching rows, rename `Network Persistent State`, relaunch | Selected when the app path is degraded and a bounded ChatGPT Chromium network-state file is observed; backup is `.wnrt-backup-*` |

The cold restart does **not** touch Cookies, Login Data, Local Storage, extensions, history, or arbitrary Electron applications. If process exit cannot be verified, the state file is left unchanged.

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

- **Session or site-data corruption** — the recovery does not clear cookies, tokens, Local Storage, or browser site data. It quarantines only Chromium transport/network state.
- **Proof of “stuck” processes or corrupt QUIC state** — a count and file presence are observations. Relief after a cold restart supports the hypothesis but does not prove root cause.
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
4. **Rollback a quarantine if needed** — quit ChatGPT, remove the newly recreated `Network Persistent State`, then rename the adjacent `.wnrt-backup-*` file to `Network Persistent State`.
5. **Proxy still dead?** Run `.\scripts\fix-wininet-proxy.cmd` or preview:
   ```powershell
   python -m windows_network_toolkit proxy-disable --dry-run
   python -m windows_network_toolkit proxy-disable --dry-run false --confirm DISABLE_WININET_PROXY
   ```
6. **Firewall hypothesis?** Manual preview only:
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
| `src/network_recovery/app_state.py` | Bounded process count, state discovery, metadata-only observation, and reversible quarantine helper |
| `src/network_recovery/remediation_executor.py` | LOW-risk allowlist + `APPLY_CHATGPT_LOW_RISK` gate |
| `src/network_recovery/scenarios/chatgpt_app_firewall.py` | Hypothesis ranking |
| `windows_network_toolkit/cli.py` | `auto-fix-chatgpt`, `bad-gateway-diagnose` subcommands |

Tests: `tests/test_network_recovery_app_state.py`, `tests/test_network_recovery_auto_fix.py`, `tests/test_network_recovery_chatgpt_scenario.py`
