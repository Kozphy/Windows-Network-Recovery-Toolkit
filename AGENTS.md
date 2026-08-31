# AGENTS.md — cross-agent summary

Short rules for AI assistants (Cursor, Codex, Copilot, etc.). Persistent Cursor rule: [`.cursor/rules/project-instructions.mdc`](.cursor/rules/project-instructions.mdc).

## Project

**Technology Risk & Control Analytics Platform** for Windows endpoint evidence — proxy drift, TLS-path comparison, incident classification, control testing, audit trails, and governance exports.

**Not** antivirus, EDR, XDR, malware attribution, or autonomous security software.

## Non-negotiable rules

| # | Rule |
| --- | ------ |
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
python -m src operator-incident --fixture tests/fixtures/operator_incident/ipv6_broken.json
python -m src.purple_team scenarios list
python -m src.purple_team validate proxy-drift-001
python -m src.purple_team benchmark --no-evidence --json
python -m windows_network_toolkit audit verify .audit/canonical_custody.jsonl --check-tip
pytest -q tests/test_policy_safety_contract.py
pytest -q tests/purple_team
pytest -q tests/test_proxy_drift_toolkit.py --basetemp=.pytest_tmp
pytest -q tests/test_procmon_filter_and_watch_soak.py --basetemp=.pytest_tmp
```

## Key paths

| Path | Role |
| ------ | ------ |
| `windows_network_toolkit/` | Primary CLI and diagnostics |
| `riskclaw/` | Product-agent contracts, SKILL.md loader, typed tools, policy adapter |
| `src/proxy_drift/` | Startup observability, boot trace, guardian, operator incident card |
| `src/purple_team/` | Purple Team validation loop (fixture sim → detect → verify → measure) |
| `scenarios/` | Purple scenario YAML (safety + rollback required) |
| `research/` | Purple RQ / hypotheses / threats to validity |
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
