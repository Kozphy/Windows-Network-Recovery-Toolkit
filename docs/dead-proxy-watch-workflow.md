# Dead proxy watch workflow

Operator runbook for **continuous detection**, **structured collection**, and **safe recovery** when WinINET points at a dead localhost proxy (`DEAD_PROXY_CONFIG`).

**Safety:** Observation is not proof. Classification is not accusation. No autonomous remediation in `proxy-watch`. CLI remediation is preview-first; one-shot PowerShell scripts may live-apply with embedded confirmation tokens.

---

## Detection loop (recommended)

```powershell
$env:PYTHONPATH = (Get-Location).Path

# 1. Point-in-time snapshot (includes health-informed classification on live Windows)
python -m windows_network_toolkit proxy-status

# 2. Path probes (direct vs proxy HTTPS)
python -m windows_network_toolkit proxy-health --json

# 3. Continuous drift collection (read-only → .audit/proxy-watch.jsonl)
python -m windows_network_toolkit proxy-watch --duration 900 --interval 2 --format human

# 4. Optional guardian preview (no registry mutation)
python -m windows_network_toolkit proxy-guardian --dry-run true

# 5. Export local incident bundle (gitignored under reports/)
python -m windows_network_toolkit dead-proxy-export
```

Fixture-safe (CI / no admin):

```powershell
python -m windows_network_toolkit proxy-status --fixture examples/evidence/DEAD_PROXY_CONFIG.json
python -m windows_network_toolkit proxy-watch --fixture tests/fixtures/proxy_watch_localhost.json --format human
```

---

## When classification is `DEAD_PROXY_CONFIG`

Evidence required (at least one):

- Health probe: `DEAD_LOCALHOST_PROXY` or `DIRECT_ONLY_WORKS`, **or**
- No TCP listener on configured localhost port (netstat correlation)

`proxy-status` on live Windows runs health probes when WinINET proxy targets localhost.

---

## When things go wrong

### Reverter / flapping (`REVERTER_SUSPECTED`)

`proxy-watch` prints operator next steps. **Do not auto-kill processes.**

1. `.\scripts\configure-cursor-no-proxy.ps1` — restart Cursor after
2. Keep `proxy-watch` read-only
3. Preview only: `proxy-disable --dry-run true`

### Guardian blocked

Guardian writes `gate_reason` to stderr and JSON:

| `gate_reason` | Meaning |
|---------------|---------|
| `classification_not_dead_proxy` | No dead proxy — no action |
| `dry_run_preview` | Preview only |
| `policy_or_confirmation_blocked` | Policy or missing `DISABLE_WININET_PROXY` |

### Browsers fail but `proxy-status` says `NO_PROXY`

Read `diagnostic_hints` in JSON output. Common causes: WinINET/WinHTTP split, per-app proxy, VPN, env vars, or **Git SSH** (not proxy).

### Live remediation

**CLI (preview-first):**

```powershell
python -m windows_network_toolkit proxy-disable --dry-run true
python -m windows_network_toolkit proxy-disable --dry-run false --confirm DISABLE_WININET_PROXY
```

**One-shot scripts (live-by-default):**

- `scripts/auto-fix-proxy.ps1` — may apply guardian with embedded token
- See [dead-proxy-guardian.md](dead-proxy-guardian.md)

---

## Audit schema (`proxy-watch.jsonl`)

Each coalesced change event includes:

| Field | Purpose |
|-------|---------|
| `schema_version` | `proxy_watch_event.v1` |
| `before_state` / `after_state` | WinINET drift |
| `health_audit` | Probes + classification |
| `classification` | e.g. `DEAD_PROXY_CONFIG` |
| `limitations` | Epistemic boundaries |
| `proof_tier` | Ordinal tier (T1–T2 typical) |
| `transition_evidence` | State machine metadata |

Never commit real `.audit/*.jsonl` — use fixtures under `tests/fixtures/`.

---

## Related

- [WORKFLOW.md](WORKFLOW.md) — developer daily workflow
- [TROUBLESHOOTING_PROXY.md](TROUBLESHOOTING_PROXY.md) — symptom guide + Git SSH vs HTTPS
- [dead-proxy-guardian.md](dead-proxy-guardian.md) — 3-layer recovery
- [incident-walkthrough-dead-proxy.md](incident-walkthrough-dead-proxy.md) — step narrative
- `examples/evidence/DEAD_PROXY_CONFIG.json` — portfolio fixture
