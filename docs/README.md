# Documentation

This folder contains the project guides, runbooks, and troubleshooting references for the **Windows Network Recovery Toolkit**: guided Windows 10/11 network diagnosis and repair workflows (batch tooling, optional Python CLIs, optional demo backend/frontend).

## Architecture (where these docs fit)

| Area | Role |
| --- | --- |
| `scripts/*.bat`, `scripts/monitor_network.ps1` | Operator-facing probes and repairs; primary beginner path. |
| `src/` (`python -m src`) | Stdlib **observe → Hypotheses(v2)** + **legacy v1** scoring + Proxy Guard CLI. |
| `network_agent/` + `hybrid_frontend/` | Local FastAPI + collector/decision/report flow (see component docstrings). |
| `backend/` + `frontend/` + `agent/` | Optional SaaS-style demo (FastAPI + Next.js + syncing agent), not required for batch repair. |

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

## Project Design

- `design_principles.md`: goals, non-goals, and documentation standards.
- `faq.md`: beginner-friendly answers to common questions.

## Skipped or out of scope here

These markdown files describe only what exists in-repo. They do **not** imply a hosted production deployment, SLAs, fleet management, or centralized log ingestion unless you add that infrastructure separately.
