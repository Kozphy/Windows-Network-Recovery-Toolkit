# Windows Network Recovery Toolkit — Cursor Session Instructions

## Project overview

**Windows Network Recovery Toolkit** is a **Technology Risk & Control Analytics Platform** for Windows endpoint reliability.

It collects deterministic evidence, classifies incidents such as `DEAD_PROXY_CONFIG`, runs control tests, gates remediation behind preview and typed confirmation, and exports audit-backed governance reports.

This project is **not** antivirus, EDR, XDR, malware attribution, or autonomous security software.

Core pipeline:

```text
Observation → Hypothesis → Proof → Policy → Remediation → Audit
```

## Safety boundaries

Always preserve these principles:

* Observation is not proof.
* Correlation is not causation.
* Classification is not accusation.
* Confidence is ordinal, not calibrated probability.
* Policy permission is not a safety guarantee.
* Recommendation is not execution authority.
* Dry-run is the default for registry-changing commands.
* Never weaken confirmation gates.
* Never add silent remediation paths.
* Never convert diagnostic evidence into malware attribution.

## Cursor / AI configuration in this repo

| File                                     | Role                                                 |
| ---------------------------------------- | ---------------------------------------------------- |
| `.cursor/rules/project-instructions.mdc` | Always-on Cursor rule for safety, tests, and commits |
| `AGENTS.md`                              | Short cross-agent summary                            |
| `instruction.md`                         | Human-readable project brief for Cursor sessions     |

`instruction.md` is context for AI sessions. The always-on safety rules belong in `.cursor/rules/project-instructions.mdc`.

---

# Core functionalities

## Evidence and diagnosis

Read-only commands:

```powershell
$env:PYTHONPATH = (Get-Location).Path

python -m windows_network_toolkit proxy-status
python -m windows_network_toolkit proxy-health --json
python -m windows_network_toolkit diagnose --proof
python -m windows_network_toolkit proxy-owner
python -m windows_network_toolkit proxy-watch --duration 300 --interval 2
```

Fixture replay without host mutation:

```powershell
python -m windows_network_toolkit proxy-status --fixture dead_proxy_59081.json
python -m windows_network_toolkit proxy-status --fixture dead_proxy_60505.json
```

## Policy-gated remediation

Preview first:

```powershell
python -m windows_network_toolkit proxy-disable --dry-run true
```

Actual registry-changing remediation requires explicit typed confirmation:

```powershell
python -m windows_network_toolkit proxy-disable --dry-run false --confirm DISABLE_WININET_PROXY
```

PowerShell helper:

```powershell
.\scripts\auto-fix-proxy.ps1
```

## Telemetry and writer attribution

* `telemetry/` — Sysmon, EventLog, ETW fixture parsers, and registry-writer fusion
* `python -m windows_network_toolkit proxy-writer-attribution`
* `python -m telemetry.cli parse-sysmon-fixture <path>`

## Governance, analytics, and platform

| Area             | Examples                                                  |
| ---------------- | --------------------------------------------------------- |
| Control and risk | `risk-assess`, `control-test`, `governance-report`        |
| Analytics        | `analytics-summary`, `analytics-export`, `powerbi-export` |
| Read-only agent  | `agent once`, `agent run`, `agent health`                 |
| HTTP API         | `backend/` — FastAPI `/trisk/*`, `/platform/*`            |

## Signature incident: dead localhost WinINET proxy

| Signal                | Typical value       |
| --------------------- | ------------------- |
| WinINET `ProxyEnable` | `1`                 |
| WinINET `ProxyServer` | `127.0.0.1:<port>`  |
| Listener on port      | None                |
| WinHTTP               | Often direct        |
| Classification        | `DEAD_PROXY_CONFIG` |

Important distinction:

`git@github.com: Permission denied (publickey)` is usually an SSH key issue, not a proxy issue. If Git over HTTPS works, the network path is likely functional.

---

# Documentation reading order

Read in this order:

| # | Document                                      | Purpose                           |
| - | --------------------------------------------- | --------------------------------- |
| 1 | `README.md`                                   | Positioning, non-claims, repo map |
| 2 | `docs/DOCUMENTATION_INDEX.md`                 | Full documentation catalog        |
| 3 | `docs/ONBOARDING.md`                          | Ten-minute engineer onboarding    |
| 4 | `docs/evidence_to_action_governance_model.md` | Six governance principles         |
| 5 | `docs/dead-proxy-guardian.md`                 | Guardian and remediation gates    |
| 6 | `docs/telemetry_registry_writer_proof.md`     | Telemetry evidence levels         |
| 7 | `docs/code-documentation-standards.md`        | Docstring style                   |

Golden fixtures for tests and demos:

```text
tests/fixtures/enert/dead_proxy_59081.json
tests/fixtures/enert/dead_proxy_60505.json
examples/evidence/DEAD_PROXY_CONFIG.json
tests/fixtures/telemetry/
```

---

# Current file structure

```text
windows_network_toolkit/     Primary CLI — proxy-status, diagnose, agent, analytics
  cli.py                     Register and verify subcommands here
  proxy_remediation.py       Gated WinINET disable; dry-run default
  proxy_guardian.py          Dead-proxy policy gate
  collectors/                Read-only evidence facades
  diagnostics/               Proxy, LAN, router evidence runners
  safety.py                  Blocked destructive actions

src/platform_core/           Policy, evidence tiers, governance envelope, audit
telemetry/                   Registry-writer telemetry; fixture-first
backend/                     FastAPI platform API
tests/                       Safety contracts, fixtures, replay
tests/fixtures/              Deterministic inputs
docs/                        Architecture, runbooks, demos
scripts/                     Operator PowerShell helpers
.cursor/rules/               Cursor project rules
.audit/                      Operator JSONL; gitignored; do not commit
reports/                     Local exports; gitignored; do not commit
```

---

# Instructions for Cursor AI sessions

## Before editing

1. Inspect nearby modules and existing tests.
2. Match existing naming, patterns, and safety model.
3. Do not invent CLI commands, APIs, flags, or files.
4. Verify available CLI commands in `windows_network_toolkit/cli.py`.
5. Prefer fixture injection using `--fixture` and `tests/fixtures/` over live registry or network changes.
6. Preserve backward-compatible CLI behavior unless the task explicitly changes behavior.

## While implementing

* Minimize scope.
* Avoid unrelated refactors.
* Preserve `limitations[]` on structured outputs.
* Use `attach_governance_envelope` where applicable.
* Keep remediation preview-first.
* Never bypass typed confirmation.
* Never turn classification into accusation.
* Never treat confidence as calibrated probability.
* Never claim malware attribution from proxy evidence alone.

Blocked by default:

* Process kill
* Firewall reset
* Network adapter disable
* Silent registry mutation
* Any destructive host action not explicitly approved by policy and confirmation gates

Check `windows_network_toolkit/safety.py` before adding actions that could affect the host.

## After changes

Run targeted checks for touched files:

```powershell
ruff check <paths-you-touched>
pytest -q tests/<relevant-area> -v
pytest -q tests/test_policy_safety_contract.py
make principles-test
```

Report missing dependencies honestly. Do not claim tests passed if they did not run.

## Git rules

Commit only when the user explicitly asks.

Never commit:

```text
__pycache__/
*.pyc
.env
secrets
.audit/
reports/
logs
```

Before suggesting a commit, check the working tree and ensure only intentional source, test, or documentation changes are staged.

## End-of-task response format

Always summarize with:

```text
Changed files:
- ...

Tests run:
- ...

Risks / limitations:
- ...

Next recommended step:
- ...
```

Be honest about skipped tests, missing dependencies, incomplete coverage, or assumptions.
