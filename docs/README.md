# Documentation

## Ten-minute orientation (new engineers)

### Repository map (what lives where)


| Path                                        | Responsibility                                                                                          |
| ------------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| `scripts/`                                  | Beginner-facing `.bat/.ps1` wrappers; safety headers describe privilege + dry-run cues.                 |
| `src/`                                      | `python -m src` — collectors, heuristic + policy pipelines, Proof Engine adapters, argparse + handlers. |
| `failure_system/`                           | Failure Knowledge System — FailureBlocks + read-only probes (distinct CLI entry).                       |
| `platform_core/` + `backend/` + `frontend/` | Optional localhost platform prototype (policy, JSONL, FastAPI `/platform`, Next.js).                    |
| `endpoint_agent/`                           | Optional observe-only cycles with optional ingest; no bundled cloud.                                    |
| `tests/`                                    | Offline regressions covering scoring, audits, remediation guards — run before risky edits.              |


### Reading order (~10 minutes)

1. `**[epistemic_model.md](epistemic_model.md)**` — **Observation ≠ Inference ≠ Proof**, confidence as ordinal ranking, replay without re-probing.
2. Root `README.md` — problem statement, demo, decision pipeline (**heuristic vs proof**), safety table, links to `**[cli_reference.md](cli_reference.md)`** for long command lists.
3. `**[decision_engine_v2.md](decision_engine_v2.md)**` — live hypotheses, proofs, audits, replay contracts.
4. `**[architecture_platform.md](architecture_platform.md)**` + `[platform_architecture.md](platform_architecture.md)` — platform Mermaid + agent → JSONL → API diagrams.
5. `**[demo_script.md](demo_script.md)**` — safe short demo paths (fleet + dashboard when enabled).
6. `docs/architecture.md` + `failure_block_contract.md` — Failure Knowledge System signal → FailureBlock flow (read-only remediation from FKS APIs).
7. `docs/proxy_guard.md` + `docs/proxy_attribution.md` — HKCU drift, honest attribution boundaries, tooling entry points.
8. `docs/proxy_investigation_workflow.md` + `docs/proxy_reasoning.md` — localhost drift incident reports vs policy-gated reasoning audit.
9. `docs/case_studies/` — evidence-calibrated incident walkthroughs (portfolio / interviews).
10. `docs/rbac_and_remediation.md` + `platform_api_contract.md` — header RBAC-lite, ingest aliases, remediation rules.

Run `pytest -q` before changing critical paths — suites stay offline and avoid destructive Windows repair.

Then dive into topical guides below as needed.

---

This folder contains the project guides, runbooks, and troubleshooting references for the **Windows Network Recovery Toolkit** and its **Failure Knowledge System**: guided Windows 10/11 network diagnosis and repair workflows (batch tooling, Python CLIs, structured FailureBlocks, optional demo backend/frontend).

## Source documentation (quick orientation)

Primary Python surfaces document themselves with **Google-style docstrings** (module summaries, Args/Returns, explicit side-effect callouts). Critical persistence or remediation paths additionally tag **Audit Notes** where forensic follow-up matters. Operational batch/PowerShell entry points under `scripts/` use `REM`/comment headers for privileges and safety envelopes. Frontend TypeScript (Next.js) uses file-level summaries where components export routes — refer to adjacent `backend/` README for API layering.

Reading order (~10 minutes for new engineers): root `README.md` → `[architecture.md](architecture.md)` (if using FKS) → `[proxy_guard.md](proxy_guard.md)` → `[proxy_attribution.md](proxy_attribution.md)` for `proxy-watch` / `proxy-report` → `[network_state_manager.md](network_state_manager.md)` when using `python -m src network-state`.

## Failure Knowledge System (start here)


| Doc                                                                      | Purpose                                                                                            |
| ------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------- |
| `[architecture.md](architecture.md)`                                     | End-to-end layers: signals → features → rules → FailureBlocks → JSONL → interfaces → human repair. |
| `[failure_block_contract.md](failure_block_contract.md)`                 | FailureBlock field contract and safe example.                                                      |
| `[failure_system_output_contract.md](failure_system_output_contract.md)` | CLI output-layer contract for `python -m failure_system diagnose` (human/json/markdown/verbose).   |
| `[interview_pitch.md](interview_pitch.md)`                               | Concise portfolio / interview framing.                                                             |
| `[safety_model.md](safety_model.md)`                                     | Diagnose-first rules; FKS never auto-repairs; local-only logs.                                     |


## Architecture (where these docs fit)


| Area                                                            | Role                                                                                                                                                                                                                                                 |
| --------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `scripts/*.bat`, `scripts/monitor_network.ps1`                  | Operator-facing probes and repairs; primary beginner path.                                                                                                                                                                                           |
| `src/` (`python -m src`)                                        | Stdlib **observe → Hypotheses(v2)** + **legacy v1** scoring + Proxy Guard CLI.                                                                                                                                                                       |
| `network_agent/` + `hybrid_frontend/`                           | Local FastAPI + collector/decision/report flow (see component docstrings).                                                                                                                                                                           |
| `failure_system/`                                               | Failure Knowledge System — read-only probes, FailureBlocks, JSONL, FastAPI + CLI (**no repair execution**).                                                                                                                                          |
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
- `**python -m src` path**: Inspect `reports/last_diagnosis.json`, `reports/last_diagnosis_live.json`, `logs/decision_audit.jsonl`, `logs/network_snapshots.jsonl`, `logs/repair_audit.jsonl`, `logs/proxy_guard.jsonl` (`proxy-watch` drift + attribution), and `reports/snapshots/` for deterministic evidence, live hypothesis exports, snapshot history, and proxy-disable audits.
- **Hybrid API path**: JSON reports under `reports/` and API payloads include diagnosis evidence; repair execution requires explicit JSON confirmation (see `network_agent/api.py` docstrings).
- **Endpoint Reliability Platform path**: Correlate `platform_data/audit.jsonl` with `platform_data/remediation_executions.jsonl` and previews; blocked rows (`result=blocked`, policy rationales) should still append even when HTTP 200 responds. Metrics (`GET /platform/metrics`) recompute from JSONL scans—skew indicates corrupt tails or malformed lines skipped by readers.

## Critical paths (where state changes matter)


| Path                                                                          | Mutation / risk surface                                            | Verification focus                                                                                               |
| ----------------------------------------------------------------------------- | ------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------- |
| Guided `.bat` repairs                                                         | Executes elevated Windows commands after confirmation              | Logs under `logs/`, script exit prompts, rerun `auto_diagnose.bat`                                               |
| `python -m src repair-safe --apply`                                           | First LOW-risk `scripts/*.bat` via `RunAs`; appends feedback JSONL | `logs/decision_feedback.jsonl`, rerun `diagnose`                                                                 |
| `python -m src proxy disable --dry-run false --confirm DISABLE_WININET_PROXY` | Mutates targeted HKCU WinINET proxy keys only                      | Compare `logs/repair_audit.jsonl`, rerun `proxy-status`, capture new `snapshot`                                  |
| `python -m src diagnose-live`                                                 | Writes live diagnosis JSON plus JSONL context                      | Verify `reports/last_diagnosis_live.json` timestamps vs `logs/decision_audit.jsonl`                              |
| `python -m src proxy-watch`                                                   | Appends drift/attribution NDJSON rows (no live rollback)           | Correlate `logs/proxy_guard.jsonl` with stderr banners; optional `--evidence-csv`                                |
| Hybrid `POST /repair/execute`                                                 | Host shell commands with `confirm: true`                           | JSON `results` array (`returncode`, stdout/stderr)                                                               |
| SaaS `/diagnose` (optional backend)                                           | SQLite usage metering + persisted rows per call                    | `/usage`, `/history` responses                                                                                   |
| Remote agent loop                                                             | Repeated HTTP posts with local probes                              | Backend logs/DB counters; bearer token posture                                                                   |
| `POST /platform/remediation/execute` (prototype)                              |                                                                    | Rows in `platform_data/remediation_executions.jsonl`, matching `audit.jsonl`, compare `SAFE_MODE` / RBAC headers |


### Endpoint Reliability Platform docs


| Doc                                                                          | Topic                                                                                                               |
| ---------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| `[architecture_platform.md](architecture_platform.md)`                       | Platform diagrams + pipeline vocabulary                                                                             |
| `[cli_reference.md](cli_reference.md)`                                       | Long CLI / agent / uvicorn inventories                                                                              |
| `[demo_script.md](demo_script.md)`                                           | Safe local demo including `demo_fleet`                                                                              |
| `[endpoint_reliability_platform.md](endpoint_reliability_platform.md)`       | Vision — toolkit vs platform                                                                                        |
| `[evidence_pipeline.md](evidence_pipeline.md)`                               | `evidence/` — attribution inputs + honest telemetry boundary                                                        |
| `[rbac_and_remediation.md](rbac_and_remediation.md)`                         | Roles vs preview / execute / ingest gates                                                                           |
| `[metrics.md](metrics.md)`                                                   | `platform_signals.jsonl` KPI names merged into `GET /platform/metrics`                                              |
| `[platform_architecture.md](platform_architecture.md)`                       | Diagrams (agent → JSONL → API)                                                                                      |
| `[platform_api_contract.md](platform_api_contract.md)`                       | `/platform/*` payloads, RBAC headers                                                                                |
| `[demo_walkthrough.md](demo_walkthrough.md)`                                 | Safe demo script incl. attribution fixture hooks                                                                    |
| `[safety_and_privacy.md](safety_and_privacy.md)`                             | Allowed / redacted fields                                                                                           |
| `[test_strategy.md](test_strategy.md)`                                       | pytest safety boundaries — offline regressions without repair scripts                                               |
| `[extension_points_multi_host_saas.md](extension_points_multi_host_saas.md)` | **Design only:** ingestion + optional remote-control interfaces; multi-host → SaaS extension points (no cloud code) |


## Tests and CI posture

Automated suites live under `**tests/`** (see `**docs/test_strategy.md**` for deliberate offline constraints).

## Supplementary tooling paths


| Path                                  | Purpose                                                                           |
| ------------------------------------- | --------------------------------------------------------------------------------- |
| `proxy_attribution/`                  | Read-only classifier/diagnostic CLI layering on Windows proxy artefacts.          |
| `src/proxy_investigation/`            | Read-only localhost proxy drift investigation → JSONL + markdown report.          |
| `proxy_reasoning/`                    | Proxy scenario ranking, verification, policy, replay audit (root package).        |
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

For **deliberate future seams** (multi-host ingestion, aggregation, SaaS wiring) without implementing cloud, see `[extension_points_multi_host_saas.md](extension_points_multi_host_saas.md)`. Operational fleet sketches live in `[fleet_architecture.md](fleet_architecture.md)`.