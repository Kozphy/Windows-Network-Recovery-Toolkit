# Developer workflow

Practical workflow for **daily development**, **proxy incident recovery**, **testing**, and **safe documentation** on the Windows Network Recovery Toolkit.

**Safety boundaries (non-negotiable):**

- Observation is not proof · Correlation is not causation · Classification is not accusation
- Confidence is ordinal, not calibrated probability
- Policy permission is not a safety guarantee · Recommendation is not execution authority
- No autonomous remediation · No malware / EDR / MITM verdict claims

---

## Environment setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
$env:PYTHONPATH = (Get-Location).Path
```

---

## Daily development

| Step | Command | Purpose |
|------|---------|---------|
| 1 | `ruff check <paths-you-touched>` | Lint changed modules only |
| 2 | `pytest -q tests/ -k "proxy or dead_proxy" -v` | Fast proxy spine |
| 3 | `pytest -q tests/reviewer/ tests/test_policy_safety_contract.py` | Safety contracts |
| 4 | `python -m windows_network_toolkit proxy-status --fixture dead_proxy_60505.json` | Golden dead-proxy fixture |
| 5 | `python -m windows_network_toolkit proxy-disable --dry-run true` | Preview remediation (no mutation) |

Before commit:

```powershell
pytest -q tests/windows_network_toolkit/test_dead_proxy_workflow.py tests/windows_network_toolkit/test_proxy_guardian.py -v
git status   # ensure .audit/, reports/, *.jsonl not staged
```

CI mirrors key checks in `.github/workflows/ci.yml` (fixture `proxy-status`, `proxy-disable --dry-run`, `diagnose --proof`).

---

## Proxy incident recovery (operator)

Use when browsers show `ERR_PROXY_CONNECTION_FAILED` but ping/TCP may still work.

```powershell
$env:PYTHONPATH = (Get-Location).Path

# Read-only evidence
python -m windows_network_toolkit proxy-status
python -m windows_network_toolkit proxy-health --json
python -m windows_network_toolkit diagnose --proof

# Optional drift collection (read-only)
python -m windows_network_toolkit proxy-watch --duration 300 --interval 2 --format human

# Export local bundle (gitignored under reports/)
python -m windows_network_toolkit dead-proxy-export

# Preview fix (default — no registry mutation)
python -m windows_network_toolkit proxy-disable --dry-run true

# Live fix (typed confirmation required)
python -m windows_network_toolkit proxy-disable --dry-run false --confirm DISABLE_WININET_PROXY
```

**One-shot script (live-by-default):** `.\scripts\auto-fix-proxy.ps1` — see [dead-proxy-guardian.md](dead-proxy-guardian.md).

Full runbook: [TROUBLESHOOTING_PROXY.md](TROUBLESHOOTING_PROXY.md) · [dead-proxy-watch-workflow.md](dead-proxy-watch-workflow.md)

---

## Reproducing dead proxy in tests (no host mutation)

| Fixture | Port | Use |
|---------|------|-----|
| `tests/fixtures/enert/dead_proxy_59081.json` | 59081 | CI golden case |
| `tests/fixtures/enert/dead_proxy_60505.json` | 60505 | Recent incident model |
| `examples/evidence/DEAD_PROXY_CONFIG.json` | 59081 | Portfolio evidence |

```powershell
python -m windows_network_toolkit proxy-status --fixture dead_proxy_60505.json
python -m windows_network_toolkit proxy-health --fixture dead_proxy_60505.json --json
python -m windows_network_toolkit diagnose --proof --fixture dead_proxy_60505.json
python -m windows_network_toolkit proxy-owner --fixture dead_proxy_60505.json
```

Expected classification: **`DEAD_PROXY_CONFIG`** — reliability triage, not malware verdict.

---

## Documenting evidence (local only)

1. Run `dead-proxy-export` after `proxy-watch` — writes `reports/dead_proxy_incident_<timestamp>/`
2. Never commit `.audit/*.jsonl`, `reports/` machine exports, or `trisk_local.db`
3. For portfolio/docs, copy **sanitized** patterns into `tests/fixtures/` or `examples/evidence/`
4. Always include `limitations[]` — see `real_evidence/case-001-dead-proxy/`

---

## Git HTTPS vs SSH (do not conflate with proxy)

| Symptom | Likely cause | Action |
|---------|--------------|--------|
| `git ls-remote https://github.com/...` works | Network + HTTPS path OK | Proxy likely fine for HTTPS |
| `git@github.com: Permission denied (publickey)` | **SSH keys**, not proxy | Fix SSH key or use HTTPS remote |
| Browser `ERR_PROXY_CONNECTION_FAILED` | WinINET dead localhost proxy | `proxy-status` → `proxy-disable` preview |

HTTPS fallback:

```powershell
git remote set-url origin https://github.com/Kozphy/Windows-Network-Recovery-Toolkit.git
git ls-remote origin
```

---

## API development (optional)

```powershell
.\start-api.ps1
# curl http://127.0.0.1:8000/platform/health
```

Proxy remediation via API still requires confirmation tokens — see `tests/test_api_proxy_disable_confirmation.py`.

---

## Related docs

| Doc | Topic |
|-----|-------|
| [TROUBLESHOOTING_PROXY.md](TROUBLESHOOTING_PROXY.md) | Symptom → command matrix |
| [dead-proxy-watch-workflow.md](dead-proxy-watch-workflow.md) | Continuous watch + export |
| [dead-proxy-guardian.md](dead-proxy-guardian.md) | Guardian + auto-fix scripts |
| [test-strategy.md](test-strategy.md) | Safety contracts + fixtures |
| [AGENTS.md](../AGENTS.md) | Agent/coding safety rules |
