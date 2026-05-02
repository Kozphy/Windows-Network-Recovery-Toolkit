# Documentation

This folder contains the project guides, runbooks, and troubleshooting references for the **Windows Network Recovery Toolkit** and its **Failure Knowledge System**: guided Windows 10/11 network diagnosis and repair workflows (batch tooling, Python CLIs, structured FailureBlocks, optional demo backend/frontend).

## Failure Knowledge System (start here)

| Doc | Purpose |
| --- | --- |
| [`architecture.md`](architecture.md) | End-to-end layers: signals → features → rules → FailureBlocks → JSONL → interfaces → human repair. |
| [`failure_block_contract.md`](failure_block_contract.md) | FailureBlock field contract and safe example. |
| [`interview_pitch.md`](interview_pitch.md) | Concise portfolio / interview framing. |
| [`safety_model.md`](safety_model.md) | Diagnose-first rules; FKS never auto-repairs; local-only logs. |

## Architecture (where these docs fit)

| Area | Role |
| --- | --- |
| `scripts/*.bat`, `scripts/monitor_network.ps1` | Operator-facing probes and repairs; primary beginner path. |
| `src/` (`python -m src`) | Stdlib **observe → Hypotheses(v2)** + **legacy v1** scoring + Proxy Guard CLI. |
| `network_agent/` + `hybrid_frontend/` | Local FastAPI + collector/decision/report flow (see component docstrings). |
| `failure_system/` | Failure Knowledge System — read-only probes, FailureBlocks, JSONL, FastAPI + CLI (**no repair execution**). |
| `backend/` + `frontend/` + `endpoint_agent/` + `platform_core/` | Optional **Endpoint Reliability Platform** prototype: FastAPI `/platform/*`, Next.js dashboard, append-only `platform_data/*.jsonl`, local collector (**no silent auto-repair**). Same paths may also host other demo APIs—see component docstrings. |

## Safety boundaries (summary)

- Batch **diagnosis** flows are read-only; **repair** scripts require Administrator and explicit confirmation where implemented.
- Firewall reset and other high-impact steps are **never** auto-chained from conservative entry points (see root `README.md` and `safety_model.md`).
- Python audit logs under `logs/` are append-only and local unless you copy them; do not treat them as telemetry to third parties by default.

## Troubleshooting (documentation map)

1. Run or review `operational_runbook.md` for sequencing.
2. Use `diagnosis_decision_tree.md` and `troubleshooting_flow.md` to correlate symptoms with scripts.
3. For intermittent issues, see `script_reference.md` and root `README.md` sections on `monitor_network.ps1`.

## Audit notes for reviewers

- **Batch path**: Timestamped logs land under `logs/`; compare before/after artifacts when validating a repair.
- **`python -m src` path**: Inspect `reports/last_diagnosis.json`, `reports/last_diagnosis_live.json`, `logs/decision_audit.jsonl`, `logs/network_snapshots.jsonl`, `logs/repair_audit.jsonl`, and `reports/snapshots/` for deterministic evidence, live hypothesis exports, snapshot history, and proxy-disable audits.
- **Hybrid API path**: JSON reports under `reports/` and API payloads include diagnosis evidence; repair execution requires explicit JSON confirmation (see `network_agent/api.py` docstrings).
- **Endpoint Reliability Platform path**: Correlate `platform_data/audit.jsonl` with `platform_data/remediation_executions.jsonl` and previews; blocked rows (`result=blocked`, policy rationales) should still append even when HTTP 200 responds. Metrics (`GET /platform/metrics`) recompute from JSONL scans—skew indicates corrupt tails or malformed lines skipped by readers.

## Critical paths (where state changes matter)

| Path | Mutation / risk surface | Verification focus |
| --- | --- | --- |
| Guided `.bat` repairs | Executes elevated Windows commands after confirmation | Logs under `logs/`, script exit prompts, rerun `auto_diagnose.bat` |
| `python -m src repair-safe --apply` | First LOW-risk `scripts/*.bat` via `RunAs`; appends feedback JSONL | `logs/decision_feedback.jsonl`, rerun `diagnose` |
| `python -m src proxy-disable` (confirmed apply) | Mutates HKCU WinINET proxy keys only | Compare `logs/repair_audit.jsonl`, rerun `proxy-status`, capture new `snapshot` |
| `python -m src diagnose-live` | Writes live diagnosis JSON plus JSONL context | Verify `reports/last_diagnosis_live.json` timestamps vs `logs/decision_audit.jsonl` |
| Hybrid `POST /repair/execute` | Host shell commands with `confirm: true` | JSON `results` array (`returncode`, stdout/stderr) |
| SaaS `/diagnose` (optional backend) | SQLite usage metering + persisted rows per call | `/usage`, `/history` responses |
| Remote agent loop | Repeated HTTP posts with local probes | Backend logs/DB counters; bearer token posture |
| `POST /platform/remediation/execute` (prototype) | May spawn allowlisted `.bat` subprocess on Windows when policy + confirmations pass | Rows in `platform_data/remediation_executions.jsonl`, matching `audit.jsonl`, compare `SAFE_MODE` / RBAC headers |

### Endpoint Reliability Platform docs

| Doc | Topic |
| --- | --- |
| [`endpoint_reliability_platform.md`](endpoint_reliability_platform.md) | Vision — toolkit vs platform |
| [`platform_architecture.md`](platform_architecture.md) | Diagrams (agent → JSONL → API) |
| [`platform_api_contract.md`](platform_api_contract.md) | `/platform/*` payloads, RBAC headers |
| [`safety_and_privacy.md`](safety_and_privacy.md) | Allowed / redacted fields |
| [`test_strategy.md`](test_strategy.md) | pytest safety boundaries — offline regressions without repair scripts |

## Tests and CI posture

Automated suites live under **`tests/`** (see **`docs/test_strategy.md`** for deliberate offline constraints).

## Supplementary tooling paths

| Path | Purpose |
| --- | --- |
| `proxy_attribution/` | Read-only classifier/diagnostic CLI layering on Windows proxy artefacts. |
| `network_agent/` + `hybrid_frontend/` | Alternate demo stacks documented in-repo; not required for `python -m src` flows. |


## Start Here

- `script_reference.md`: what each script does and when to use it.
- `operational_runbook.md`: step-by-step troubleshooting process.
- `safety_model.md`: safety rules and boundaries.

## Diagnosis

- `diagnosis_decision_tree.md`: how automatic diagnosis chooses a recommendation.
- `troubleshooting_flow.md`: manual troubleshooting flow.
- `script_reference.md`: includes the connection exhaustion check for socket leaks and ephemeral port exhaustion.

## Common Problems

- `proxy_error.md`: explains `ERR_PROXY_CONNECTION_FAILED`.
- `ping_ok_but_browser_fails.md`: explains why ping can work while browser traffic fails.
- `proxy_known_good_snapshot.md`: named baseline capture / diff / restore for Windows proxy stacks (`python -m src proxy-snapshot`).

## Project Design

- `design_principles.md`: goals, non-goals, and documentation standards.
- `faq.md`: beginner-friendly answers to common questions.

## Skipped or out of scope here

These markdown files describe only what exists in-repo. They do **not** imply a hosted production deployment, SLAs, fleet management, or centralized log ingestion unless you add that infrastructure separately.
