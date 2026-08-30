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

## Roadmap-driven delivery

When asked to continue or upgrade Decision Provenance work:

1. Read [`docs/decision-provenance-roadmap.md`](docs/decision-provenance-roadmap.md).
2. Check whether the prerequisite pull request is merged and whether required CI is passing.
3. Select only the first eligible unchecked implementation item.
4. Create or use one focused `agent/<short-description>` branch.
5. Implement one bounded capability; do not bundle unrelated refactors or integrations.
6. Preserve v2 compatibility unless an approved issue explicitly authorizes migration.
7. Preserve preview-only remediation and typed human confirmation.
8. Add deterministic unit, invariant, and compatibility tests for the new behavior.
9. Run focused tests first, then the relevant repository gates.
10. Open a **draft** pull request with problem, non-goals, evidence, risks, and limitations.
11. Update a roadmap checkbox only after implementation and relevant tests pass.
12. Never merge automatically; a human retains final merge authority.
13. Stop rather than stack new work on a failing or unreviewed prerequisite PR.

## Pull-request boundaries

A focused implementation pull request should normally have:

- one primary capability;
- a small, coherent set of changed files;
- explicit non-goals;
- deterministic tests;
- no weakening of safety controls;
- an independently reversible diff.

Workflow, dependency, permission, or secret-handling changes require explicit human review and must not be silently combined with feature work.

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
pytest -q tests/decision_provenance
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
| `docs/decision-provenance-roadmap.md` | Ordered Decision Provenance delivery plan |
| `docs/ONBOARDING.md` | Human onboarding |
| `docs/startup-observability.md` | Startup observability architecture |
| `docs/openclaw-coding-agent.md` | Policy-gated OpenClaw coding agent (draft PR only) |
| `skills/wnrt-coder/` | OpenClaw skill for controlled coding automation |

## Deeper reference

Full CLI groups, confirmation tokens, and test conventions were consolidated into `.cursor/rules/project-instructions.mdc`. For operator runbooks: `docs/TROUBLESHOOTING_PROXY.md`, `docs/dead-proxy-guardian.md`, `docs/startup-observability.md`.
