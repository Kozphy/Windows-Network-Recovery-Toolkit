# Changelog

All notable changes to this project are documented here.

## Unreleased

### Added — Evidence Case model
- `src/platform_core/evidence_case/` — typed pipeline: Observation → … → Learning
- JSON Schema export at `schemas/evidence_case.schema.json`
- CLI: `evidence-case create|report|validate|schema`
- Tests: `tests/test_evidence_case.py`

### Added — URL Evidence Diagnostic
- `src/platform_core/url_diagnostics/` — DNS/TCP/TLS/HTTP probes, soft-404 detection, LinkedIn domain profile, classifier
- CLI: `python -m windows_network_toolkit url-diagnose --url ... --json`
- Tests: `tests/test_url_diagnose.py` (mocked, no live LinkedIn in CI)

### Added — Enterprise Technology Risk & Control Analytics Platform
- Full governance pipeline: Business Objective → Asset → Threat → Control → Testing → Finding → Risk → Remediation → Governance → Audit → Learning
- `src/platform_core/business_objectives/`, `assets/`, `threats/`, `controls/`, `control_testing/`, `findings/`, `risk_assessment/`, `remediation_lifecycle/`, `governance_metrics/`, `enterprise_audit/`, `enterprise_learning/`, `risk_platform/`
- CLI: `python -m windows_network_toolkit risk-analytics`
- API: `/platform/risk-analytics/*` (assess, governance-dashboard, executive-summary, risk-register, export)
- Tests: `tests/test_enterprise_risk_platform.py` (12 tests)
- Docs: `docs/enterprise-risk-platform/` (architecture, control framework, risk register, governance dashboard, audit trail, executive summary)

### Added — Portfolio platform
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
