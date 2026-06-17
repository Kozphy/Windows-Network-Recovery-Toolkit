# Documentation Index

10-minute orientation for engineers and auditors. All paths are relative to the repository root.

## What this repository is

A **local-first Windows endpoint reliability toolkit** with a growing **Decision Intelligence Platform**:

- **Primary CLI:** JSON-first diagnostics and policy-gated remediation (`python -m windows_network_toolkit`)
- **Legacy shim:** `python -m src` (deprecated for proxy commands)
- Append-only JSONL audit trails (`.audit/` + legacy `logs/`) and deterministic replay
- FastAPI platform API (`backend/`) with optional PostgreSQL
- Multi-domain adapters (Windows, Security, Cloud, Infrastructure, Market Events)
- Research-only market catalyst monitoring (no trade execution)

## Portfolio pack (recruiters, Big 4, interviews)

| Doc | Purpose |
|-----|---------|
| **[README_BIG4_PORTFOLIO.md](README_BIG4_PORTFOLIO.md)** | **Big 4 / Risk Advisory portfolio index (start here)** |
| [big4_interview_positioning.md](big4_interview_positioning.md) | Core Big 4 framing and STAR story |
| [technology_risk_control_matrix.md](technology_risk_control_matrix.md) | Control testing matrix |
| [interview_pitch_90_seconds.md](interview_pitch_90_seconds.md) | 90-second spoken pitch |
| [interview_pitch_5_minutes.md](interview_pitch_5_minutes.md) | 5-minute detailed pitch |
| [big4_demo_flow.md](big4_demo_flow.md) | Live interview demo script |
| [big4_interviewer_q_and_a.md](big4_interviewer_q_and_a.md) | Anticipated Q&A |
| [resume_bullets_big4.md](resume_bullets_big4.md) | Resume bullets (Risk / Consulting / FinTech) |
| [consulting_case_study.md](consulting_case_study.md) | STAR consulting case study |
| [fintech_operational_risk_case.md](fintech_operational_risk_case.md) | FinTech operational resilience angle |
| [linkedin_big4_portfolio_post.md](linkedin_big4_portfolio_post.md) | LinkedIn announcement draft |
| [control-matrix.md](control-matrix.md) | Portfolio control matrix summary |
| [sql_analytics_queries.md](sql_analytics_queries.md) | **12+ KPI SQL queries with interpretation** |
| [portfolio-summary.md](portfolio-summary.md) | General portfolio summary |
| [case-study-1-proxy-drift.md](case-study-1-proxy-drift.md) | Dead proxy drift case study |
| [case-study-2-unknown-local-proxy-listener.md](case-study-2-unknown-local-proxy-listener.md) | Unknown listener case study |
| [case-study-3-endpoint-reliability-decision-engine.md](case-study-3-endpoint-reliability-decision-engine.md) | Decision engine case study |
| [consulting-report.md](consulting-report.md) | Manager-facing risk assessment |
| [demo-video-script.md](demo-video-script.md) | 3–5 minute demo script |
| [ai_investigation_platform_architecture.md](ai_investigation_platform_architecture.md) | AI-assisted investigation platform design |
| [rag_investigation_design.md](rag_investigation_design.md) | RAG retrieval system (SQLite → pgvector) |
| [hypothesis_engine_design.md](hypothesis_engine_design.md) | Multievidence hypothesis engine |
| [decision_intelligence_platform_design.md](decision_intelligence_platform_design.md) | Federated 5-domain DIP (IT, Security, Risk, Business, Compliance) |
| [screenshots/README.md](screenshots/README.md) | Screenshot placeholders |

## Golden case (59081)

Dead WinINET localhost proxy — see [case-studies/dead-localhost-proxy.md](case-studies/dead-localhost-proxy.md).

```powershell
python -m windows_network_toolkit proxy-status --fixture tests/fixtures/enert/dead_proxy_59081.json
python -m windows_network_toolkit diagnose --proof --fixture tests/fixtures/enert/dead_proxy_59081.json
```

## Core flows

### 1. Windows endpoint reliability (final causation)

```text
proxy-watch (drift) → registry_writer_proof + port_owner + process_tree + proxy_path_proof → final_causation verdict
```

Commands:

```powershell
python -m src proxy-watch --final-causation
python -m src proxy-causation --since-minutes 30 --format markdown
python -m src proxy-causation --fixture tests/fixtures/proxy_causation/scenario1_proven_writer_port_owner
```

Modules: `src/proxy_guard/registry_writer_proof.py`, `final_causation.py`, `port_owner.py`, `process_tree.py`, `proxy_path_proof.py`

### 2. Multi-domain decision platform (fixture-based)

```text
NormalizedEvent → Evidence → Hypotheses → Decisions → Policy → Audit → Replay → Metrics
```

Commands:

```powershell
python -m src platform events
python -m src platform decide --event-id win-proxy-localhost-001
python -m src platform replay
```

Modules: `src/core/`, `src/domains/`, `src/platform_handlers.py` · Doc: [multi_domain_decision_platform.md](multi_domain_decision_platform.md) · Tests: `tests/test_multi_domain_platform.py`

### 3. Windows endpoint reliability (classic)

```text
Signals → FailureBlocks → Hypothesis/Evidence → Policy (ALLOW/PREVIEW/BLOCK) → Preview (dry-run default)
```

Entry: `src/cli.py` · Tests: `tests/test_policy_safety_contract.py`, `tests/test_replay_determinism.py`

### 2. Shared decision engine

```text
EvidenceItem[] + CandidateDecision[] → score → rank → content_digest
```

Entry: `src/decision_engine/decision_engine.py` · Tests: `tests/decision_engine/`

### 3. Multi-domain platform

```text
AdapterContext → collect_observations → derive_evidence → run_shared_reasoning → DomainPipelineResult
```

Entry: `platform_core/decision_platform/` · Diagram: `docs/decision_platform_architecture.md` · Tests: `tests/decision_platform/`

### 4. Decision Intelligence API

```text
POST /decision-intelligence/{events|evidence|decisions|outcomes} → store (JSONL or PostgreSQL)
GET /decision-intelligence/metrics · POST /decision-intelligence/replay
```

Entry: `backend/decision_intelligence/routes.py` · Schema: `platform_core/db/decision_intelligence_schema.sql`

### 5. Outcome learning

```text
DecisionOutcome → evaluate → LearningMetrics → replay digest
```

Entry: `platform_core/outcome_learning/` · Fixture: `fixtures/outcome_learning/outcomes.json`

## Safety boundaries (non-negotiable)

| Boundary | Enforcement |
|----------|-------------|
| No silent remediation | Policy gates + dry-run defaults on API previews |
| Observation ≠ proof | Documented in adapters and market events module |
| Research ≠ execution | Market module blocks trade execution paths |
| Replayable decisions | SHA-256 `content_digest` / `engine_digest` on scoring paths |
| RBAC on API writes | `backend/platform_auth.py` + `platform_core/rbac.py` |

## Module map

| Path | Responsibility |
|------|----------------|
| `src/` | Windows CLI, collectors, market events CLI |
| `platform_core/` | Shared models, policy, SRE, decision platform, outcome learning |
| `src/decision_engine/` | Deterministic scoring and ranking |
| `src/knowledge/` | Versioned YAML facts (separate from code) |
| `backend/` | FastAPI routes, auth, metrics |
| `knowledge/` | Bundled YAML knowledge files |
| `fixtures/` | Deterministic test and demo inputs |
| `deploy/` | Prometheus/Grafana provisioning |

## Running tests

```powershell
$env:PYTHONPATH = (Get-Location).Path
pytest -q
```

Pytest uses `--import-mode=importlib` (see `pytest.ini`) to avoid duplicate test module name collisions.

## Related docs

| Doc | Topic |
|-----|-------|
| `docs/case-studies/dead-localhost-proxy.md` | Golden 59081 dead proxy case |
| `docs/classification-model.md` | 12 primary labels + secondary signals |
| `docs/proof-vs-observation.md` | Proof envelope vs observation |
| `docs/interview-case-study.md` | Portfolio STAR narrative |
| `docs/three-minute-demo-script.md` | 3-minute fixture demo |
| `docs/big4-cyber-risk-positioning.md` | Cyber risk / audit framing (legacy — see README_BIG4_PORTFOLIO) |
| `docs/faang-platform-engineering-positioning.md` | Platform engineering framing |
| `docs/evidence_model.md` | Canonical evidence levels |
| `docs/policy_model.md` | Canonical policy decisions |
| `docs/observability.md` | Metrics and dashboard |
| `docs/demo_5_min.md` | 5-minute portfolio demo |
| `labs/README.md` | Experimental modules (not mainline) |
| `docs/decision_platform_architecture.md` | Multi-domain architecture diagram |
| `docs/decision_platform_migration.md` | Phased adapter/API wiring plan |
| `docs/production_shape_upgrade.md` | Production-shape portfolio upgrade |
| `docs/demo_production_5_min.md` | 5-minute production demo |
| `docs/sre_interview_walkthrough.md` | SRE portfolio narrative |
| `docs/security_tooling_walkthrough.md` | Security / forensics narrative |
| `docs/platform_engineering_walkthrough.md` | Platform engineering narrative |
| `docs/production_readiness.md` | Deployment and readiness checklist |
| `docs/test_strategy.md` | Safety regression strategy |
| `docs/platform_engineering_gap_report.md` | README vs repo reality audit |
| `docs/proxy_green_definition.md` | Proxy health definition |

## Audit checklist

1. Verify `content_digest` / `engine_digest` unchanged after scoring changes (`pytest tests/decision_engine`).
2. Confirm API mutations require RBAC headers (`tests/test_decision_intelligence_api.py`).
3. Confirm CLI fixture demos pass in CI (`ci.yml` smoke step).
4. Review append-only stores under `PLATFORM_DATA_DIR` for tamper evidence.
