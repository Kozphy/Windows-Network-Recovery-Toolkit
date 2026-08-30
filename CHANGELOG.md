# Changelog

All notable changes to this project are documented here.

## Unreleased

### Added — Audit custody Level 1 + tip anchor

- Canonical hash-chained sink: `.audit/canonical_custody.jsonl` (`WNT_AUDIT_DIR`)
- Tip anchor sibling: `.audit/canonical_custody.tip.json`
- Dual-write from `proxy-guardian`, `proxy-fix`, `ensure-proxy-health` into custody
- CLI: `audit verify --check-tip` / `--require-tip`
- Docs: `docs/audit-custody.md`
- Tests: `tests/platform_core/audit/test_custody_tip_anchor.py`

### Added — Startup observability (v0.3.0)

- `src/proxy_drift/` — combined install (`install-startup-observability`), boot trace task, dead-proxy guardian, evidence bundle, operator report, bounded `safe-search`
- CLI (`python -m src`): `install-startup-observability`, `collect-evidence-bundle`, `startup-observability-report`, `install-boot-trace-task`, `uninstall-startup-observability`
- Scripts: `scripts/install-startup-observability.ps1`, `scripts/collect-evidence-bundle.ps1`, `scripts/install-proxy-boot-trace-task.ps1`
- Docs: `docs/startup-observability.md`; updates to `docs/dead-proxy-guardian.md`, `docs/cli_reference.md`, `SYSTEM_DESIGN.md`, `README.md`
- Tests: `tests/test_proxy_drift_toolkit.py`
- Pytest: `--basetemp=.pytest_tmp` in `pytest.ini` for Windows temp isolation

### Fixed

- `safe-search` — explicit scan roots under `%TEMP%` are no longer skipped when a path segment contains `temp`

### Added — AI evals feedback loop

- `src/platform_core/ai_evals/` — fixture-only GenAI eval harness (schemas, evaluator, failure taxonomy, policy gates, report)
- `examples/ai_evals/support_bot_cases.json` — 8 support-bot RAG eval cases (no live model calls)
- CLI: `python -m windows_network_toolkit ai-eval --cases ... --format markdown|json`
- Docs: `docs/ai-evals-feedback-loop.md`; README and documentation index updates
- Tests: `tests/ai_evals/` (19 tests)

### Added — Technology Risk & Control Analytics Platform upgrade

- Canonical research docs: `research-framing`, `evidence-model`, `classification-taxonomy`, `proof-tiers`, `policy-gates`, `evaluation`, `limitations`, `safety-model`, `msc-application-summary`
- Six demo fixture packs under `fixtures/{dead_proxy_config,...}/` with expected classification/policy/report files
- 15-scenario evaluation harness: `tests/fixtures/evaluation/scenarios_15.json`, `tests/evaluation/test_scenario_matrix_15.py`
- Valid hash-chained audit sample: `tests/fixtures/risk_analytics/audit_sample_chained/`
- `reports/sample_governance_report.md` (UTF-8 committee template)
- `analytics/powerbi/schema.md` and `analytics/powerbi/sample_csv/` sample exports
- CLI aliases: `export-powerbi`, `replay-demo`; `diagnose --proof` wired to full proof envelope
- Code adapters: `classification/adapters.py`, `policy/outcome_normalizer.py`, proof tier T5 + `map_proof_tier_to_evidence_tier()`
- `docs/upgrade-deliverables.md`, `docs/test-control-matrix.md`

### Added
- `windows_network_toolkit/` — Endpoint Reliability Decision Platform facade (collectors, evidence, decision, policy, remediation, audit, API)
- `python -m toolkit replay` CLI for non-Windows fixture replay
- ERP FastAPI routes: `GET /health`, `GET /platform/status`, `POST /platform/diagnose`, timeline/decision/audit/replay/confirm
- Static portfolio dashboard at `GET /dashboard/`
- Example JSONL fixtures under `windows_network_toolkit/examples/`
- Docs: `docs/endpoint_reliability_platform.md`, `docs/case_study_mttr_evidence_diagnosis.md`

### Added
- Multi-domain decision platform: `src/core/` models and engines, `src/domains/` fixture adapters (Windows, Security, Cloud, Infrastructure, Market).
- CLI: `python -m src platform {events|evidence|decide|outcome|replay|metrics}`.
- 16 domain fixtures under `tests/fixtures/domains/`.
- `tests/test_multi_domain_platform.py` (19 tests).

## Previous

### Added

- Automatic read-only diagnosis with `auto_diagnose.bat`.
- Guided repair flow with `auto_fix.bat`.
- Timestamped local diagnostic logs.
- Diagnosis decision tree documentation.
- Production-style documentation set:
  - Script reference
  - Operational runbook
  - Safety model
  - Design principles
  - FAQ
  - Contributing guide
  - Security policy

### Changed

- README now presents the recommended diagnose-first workflow.
- Documentation now emphasizes safe defaults and manual firewall reset.

## 0.1.0

### Added

- Initial Windows network repair scripts:
  - `one_click_fix.bat`
  - `check_network.bat`
  - `reset_dns.bat`
  - `reset_proxy.bat`
  - `reset_firewall.bat`
- Beginner troubleshooting documentation for proxy, DNS, and browser failure scenarios.
