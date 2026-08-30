# AGENTS.md — cross-agent summary

Short rules for AI assistants (Cursor, Codex, Copilot, etc.). Persistent Cursor rule: [`.cursor/rules/project-instructions.mdc`](.cursor/rules/project-instructions.mdc).

## Project

**Technology Risk & Control Analytics Platform** for Windows endpoint evidence — proxy drift, TLS-path comparison, incident classification, control testing, audit trails, and governance exports.

**Not** antivirus, EDR, XDR, malware attribution, or autonomous security software.

## Non-negotiable rules

| # | Rule |
|---|------|
| 1 | Use evidence tiers, ordinal confidence, and audit-backed reasoning — no false certainty |
| 2 | Remediation is policy-gated; **dry-run / preview by default** |
| 3 | Never change risky Windows/network state without explicit user confirmation + typed token |
| 4 | Prefer deterministic fixtures over live speculation |
| 5 | Separate Observation, Hypothesis, Proof, Policy, Remediation, and Audit |
| 6 | Inspect nearby code and tests before editing; preserve CLI backward compatibility unless asked |
| 7 | Run smallest relevant tests first; report missing deps honestly |
| 8 | Update docs and tests with new features |
| 9 | Do not commit `__pycache__/`, secrets, logs, or generated junk — commits only when user asks |
| 10 | Summarize: changed files, tests run, risks, next step |

## Epistemic boundaries

Observation ≠ proof · Correlation ≠ causation · Classification ≠ accusation · Policy allow ≠ safety guarantee.

Preserve `limitations[]`. Blocked actions live in `windows_network_toolkit/safety.py` (no process kill, firewall reset, adapter disable by default).

## Quick commands

```powershell
$env:PYTHONPATH = (Get-Location).Path
python -m windows_network_toolkit proxy-status --fixture dead_proxy_60505.json
python -m windows_network_toolkit proxy-disable --dry-run true
python -m src install-startup-observability --json
python -m src collect-evidence-bundle
python -m src ensure-proxy-health
python -m src procmon-filter-set
python -m src proxy-watch --interval 3 --soak-minutes 2 --exit-on-rewrite
python -m windows_network_toolkit audit verify .audit/canonical_custody.jsonl --check-tip
pytest -q tests/test_policy_safety_contract.py
pytest -q tests/test_proxy_drift_toolkit.py --basetemp=.pytest_tmp
pytest -q tests/test_procmon_filter_and_watch_soak.py --basetemp=.pytest_tmp
```

## Key paths

| Path | Role |
|------|------|
| `windows_network_toolkit/` | Primary CLI and diagnostics |
| `src/proxy_drift/` | Startup observability, boot trace, guardian, evidence bundle |
| `src/cli.py` | Extended operator CLI (`python -m src`) |
| `src/platform_core/` | Policy, governance envelope, audit |
| `src/platform_core/audit/` | Hash-chained custody + tip anchor (`docs/audit-custody.md`) |
| `telemetry/` | Registry-writer telemetry (fixture-first) |
| `tests/fixtures/` | Deterministic test inputs |
| `docs/ONBOARDING.md` | Human onboarding |
| `docs/startup-observability.md` | Startup observability architecture |
| `docs/openclaw-coding-agent.md` | Policy-gated OpenClaw coding agent (draft PR only) |
| `skills/wnrt-coder/` | OpenClaw skill for controlled coding automation |

## Deeper reference

Full CLI groups, confirmation tokens, and test conventions were consolidated into `.cursor/rules/project-instructions.mdc`. For operator runbooks: `docs/TROUBLESHOOTING_PROXY.md`, `docs/dead-proxy-guardian.md`, `docs/startup-observability.md`.

## Cursor Cloud specific instructions

The startup update script provisions a `.venv` (editable `pip install -e ".[dev]"`) and `frontend` npm deps. Notes for running/testing here:

- **Interpreter:** always use the repo `.venv` (`.venv/bin/python`, `.venv/bin/ruff`, `.venv/bin/pytest`). `make` auto-detects `.venv`. The runtime is Python 3.12 (repo requires `>=3.11`); CI pins 3.11.
- **PYTHONPATH:** several entrypoints/tests expect repo root on `PYTHONPATH` — `export PYTHONPATH=$(pwd)` before running CLIs or ad-hoc scripts.
- **Everything is fixture-first and local:** no Postgres/Redis needed. The API defaults to append-only JSONL storage + in-memory queue.
- **Services (all optional except the CLI):**
  - Core CLI: `.venv/bin/python -m windows_network_toolkit proxy-status --fixture fixtures/proxy/dead-localhost-proxy.json`
  - API: `PLATFORM_FIXTURE_MODE=1 .venv/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000` (health: `/health`, `/platform/health`, `/trisk/health`). RBAC via `X-Api-Token: dev-trisk-token` + `X-Api-Role` (or `X-Operator-Role`).
  - Frontend dashboard: `npm --prefix frontend run dev` (port 3000). Needs `frontend/.env.local` with `NEXT_PUBLIC_PLATFORM_API=http://127.0.0.1:8000` (git-ignored; not created by the update script — copy `frontend/.env.local.example`). The `/platform` page works without Supabase; Supabase vars only power the separate SaaS auth demo.
- **Tests:** `.venv/bin/python -m pytest -q` runs the full suite. Known caveat: ~21 Windows-gated proxy tests (e.g. `tests/test_proxy_endpoint_reliability.py`, `tests/windows_network_toolkit/test_proxy_guardian.py`) pass individually but fail in the full run on Linux due to pre-existing `platform.system` mock/ordering leakage — not an environment problem. The authoritative Linux gate is the ordered safety-contract sequence in `.github/workflows/ci.yml` (`test` job) plus `tests/integration_linux`, which pass.
- **Lint:** `.venv/bin/ruff check .` currently reports pre-existing import-order (`I001`) findings on this branch; CI reports Ruff lint and format results as an advisory legacy baseline.
