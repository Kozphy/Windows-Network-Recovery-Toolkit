# Technology Risk & Control Analytics Platform

*(Repository: Windows Network Recovery Toolkit)*

**Portfolio title:** Technology Risk & Control Analytics Platform — Windows endpoint reliability, control validation, and auditable remediation decisions.

**Status:** Independently developed enterprise-style **reference implementation** — not production deployment at a named institution.

### Reviewer quick scan (30 seconds)

| Question | Answer |
|----------|--------|
| **What problem?** | Windows proxy/network drift breaks apps while basic connectivity tests pass |
| **What's distinctive?** | Evidence tiers, policy-gated preview, hash-chained audit, reproducible B0–B3 benchmark |
| **Empirically evaluated?** | Dataset v1 (22 fixture scenarios), bootstrap CIs, ablations A1–A7, interaction factorials |
| **Not verified?** | Live enterprise MTTR, field recovery timing, production safety at scale |
| **Reproduce?** | [`REPRODUCING.md`](REPRODUCING.md) · `./scripts/reproduce.ps1` · `make research` |

**Enterprise docs:** [Executive summary](docs/executive-summary.md) · [Case study](docs/case-study.md) · [Portfolio summary](docs/portfolio-summary.md) · [Documentation index](docs/DOCUMENTATION_INDEX.md) · [Gap analysis](docs/research/GAP_ANALYSIS.md)

---

## Executive Summary

Enterprise Windows endpoints can **drift away from approved network baselines** — dead localhost proxies, WinINET/WinHTTP mismatches, TLS path divergence — while ping and DNS still succeed. Teams troubleshoot with ad-hoc registry resets, inconsistent narratives, and **no replayable audit trail**.

This platform converts operational telemetry into **control evidence**, **policy-gated decisions**, and **hash-chained custody records**. A Purple Team overlay validates whether detection and response controls work — using **fixture-driven, deny-by-default** simulation (not EDR, not malware attribution).

```text
Enterprise Problem → Evidence → Detection → Risk Assessment → Policy → Action → Verification → Audit → Outcome
```

**Quick start (read-only, any OS):**

```powershell
$env:PYTHONPATH = (Get-Location).Path
python -m windows_network_toolkit proxy-status --fixture examples/evidence/DEAD_PROXY_CONFIG.json
python -m src.purple_team scenarios list
```

---

## Enterprise Problem

| Dimension | Detail |
|-----------|--------|
| **Who** | IT Operations, endpoint support, Security triage, Technology Risk, Internal Audit |
| **What** | Browsers and LOB apps fail; network tests pass; root cause often local proxy drift |
| **Why it matters** | Productivity loss, repeat incidents, control exceptions, false security escalations |
| **If unaddressed** | Unsafe remediation, non-replayable decisions, weak committee evidence |

**This system does not claim** to eliminate these risks. It **structures** detection, decision, and evidence so residual risk is visible and testable.

---

## Why Existing Approaches Fail

| Approach | Gap |
|----------|-----|
| Ad-hoc PowerShell fixes | No proof tier, preview, verification, or hash-chained audit |
| Generic EDR/AV | Different problem domain — not proxy drift analytics |
| Ticketing-only GRC | Records decisions — does not collect endpoint evidence |
| Manual runbooks | High variance; cannot replay or benchmark detection quality |

See [business-case.md](docs/business-case.md) · [tradeoffs.md](docs/tradeoffs.md)

---

## Business Impact

**Intended benefits** (measurable via [kpi-framework.md](docs/kpi-framework.md) — no fabricated ROI):

- Shorter, more consistent diagnosis (structured evidence vs guesswork)
- Reduced unsafe registry mutation (preview + confirmation default)
- Clearer IT / Security / Risk ownership ([stakeholder-map.md](docs/stakeholder-map.md))
- Traceability from signal → decision → action → verification
- Demonstrable control-test and purple-validation discipline

---

## System Boundary

| In scope | Out of scope |
|----------|--------------|
| Evidence collection, classification, control tests | Malware detection / EDR replacement |
| Policy-gated remediation **previews** | Autonomous high-risk apply |
| Hash-chained local audit | WORM / SIEM / formal audit opinions |
| Purple fixture validation | Live offensive emulation in CI |
| Governance exports (management information) | SOC 2 / ISO / PCI certification |

Full boundary: [system-boundary.md](docs/system-boundary.md) · ADR: [adr/0001-system-boundary.md](docs/adr/0001-system-boundary.md)

```text
Automation (read-only)  →  evidence, classify, control test, audit append
Human review            →  ambiguous labels, attribution gaps
Governance workflow     →  registry apply, purple live mutation
Manual exception        →  blocked actions (process kill, firewall reset)
```

---

## Stakeholders

| Stakeholder | Primary value |
|-------------|---------------|
| IT Operations | Faster dead-proxy triage; preview before reset |
| Security | Non-accusatory labels; attribution tier caps |
| Technology Risk | CTRL-001–010 mapping; risk register |
| Internal Audit | Hash chain verify; custody without token leakage |
| Platform Engineering | CI safety contracts; replay determinism |

Details: [stakeholder-map.md](docs/stakeholder-map.md)

---

## Decision & Governance Model

Six principles ([evidence_to_action_governance_model.md](docs/evidence_to_action_governance_model.md)):

1. Observation ≠ proof
2. Correlation ≠ causation
3. Confidence ≠ certainty (ordinal, not probability)
4. Classification ≠ accusation
5. Policy allow ≠ safety guarantee
6. Recommendation ≠ execution authority

Pipeline: [decision-model.md](docs/decision-model.md)

```text
Telemetry → Normalize → Detect → Control evaluate → Policy gate → Preview/Apply → Verify → Audit
```

Policy outcomes: `BLOCK` · `PREVIEW_ONLY` · `REQUIRE_HUMAN_APPROVAL` · `ALLOW` (apply still requires confirmation when destructive).

---

## Architecture

```text
┌─────────────────────────────────────────────────────────────────┐
│  CLIs: windows_network_toolkit · src · src.purple_team          │
├─────────────────────────────────────────────────────────────────┤
│  Collectors → Classification → Control tests → Policy engine    │
│  Remediation preview · Verification · Governance envelope       │
├─────────────────────────────────────────────────────────────────┤
│  Audit: hash-chained JSONL + tip anchor (.audit/)               │
├─────────────────────────────────────────────────────────────────┤
│  Optional: FastAPI backend · Power BI export · NiceGUI dashboard│
└─────────────────────────────────────────────────────────────────┘
```

Deep dive: [architecture.md](docs/architecture.md) · Purple: [purple_team/architecture.md](docs/purple_team/architecture.md) · Infographic: [architecture-infographic.md](docs/architecture-infographic.md)

---

## End-to-End Workflow

### Blue Team (reliability + controls)

```text
proxy-status / diagnose
        ↓
Classify (limitations[], proof tier T0–T5)
        ↓
Control tests (PASS/FAIL/PARTIAL/NOT_TESTED)
        ↓
Policy → remediation PREVIEW (dry-run default)
        ↓
[Human confirmation] → apply → verify
        ↓
audit verify · governance-report
```

### Purple Team (control validation — prototype)

```text
Scenario YAML → safety gate → fixture simulate → detect → respond (preview) → verify → benchmark
```

---

## Control Framework

Designed to **support control evidence generation** — not regulatory attestation.

| ID | Objective | Test hook |
|----|-----------|-----------|
| CTRL-001 | Dead WinINET proxy detection | `proxy-status`, diagnose |
| CTRL-002 | WinINET/WinHTTP alignment | Stack contrast |
| CTRL-009 | Policy-gated safe remediation | `--dry-run` default; CI contracts |
| CTRL-010 | Audit hash chain integrity | `audit verify --check-tip` |

Full matrix: [control-matrix.md](docs/control-matrix.md) · Methodology: [control-testing-methodology.md](docs/control-testing-methodology.md)

---

## Risk & Failure Handling

- **Risk register:** [risk-register.md](docs/risk-register.md)
- **Failure taxonomy:** [failure-taxonomy.md](docs/failure-taxonomy.md) (F1–F9, fail-safe defaults)
- **Threat model:** [threat-model.md](docs/threat-model.md)

Policy and authorization failures **fail closed**. Audit write failures **soft-fail** with documented limitation (R-015).

---

## Auditability

**Who · What · Resource · When · Decision · Result** — via hash-chained custody.

| Question | Command / path |
|----------|----------------|
| Chain intact? | `python -m windows_network_toolkit audit verify .audit/canonical_custody.jsonl --check-tip` |
| What was decided? | `.audit/canonical_custody.jsonl` |
| Claim strength vs execution? | `governance` envelope on JSON outputs |

Confirmation **token values are never stored** — only `confirmation_supplied: true/false`.

Docs: [audit-custody.md](docs/audit-custody.md) · [audit-hash-chain-explained.md](docs/audit-hash-chain-explained.md)

---

## Business Metrics / KPIs

| Category | Examples | Source |
|----------|----------|--------|
| Engineering | Replay determinism, safety contract pass, purple F1 | CI jobs |
| Operational | MTTD/MTTR (proposed if fleet deployed) | Guardian JSONL, watch logs |
| Governance | Control failure rate, traceable decision % | governance-report |

Framework: [kpi-framework.md](docs/kpi-framework.md) · SLO framing: [slo-endpoint-reliability.md](docs/slo-endpoint-reliability.md)

**Do not fabricate** production ROI or achieved MTTR numbers.

---

## Technical Architecture

| Layer | Technology |
|-------|------------|
| Language | Python 3.11+ |
| CLI / models | Pydantic v2, JSON-first output |
| Policy / audit | `src/platform_core/` |
| Windows collectors | Registry, netstat, probes, optional Sysmon import |
| API | FastAPI + SQLModel (SQLite demo / Postgres optional) |
| Purple Team | YAML scenarios, fixture simulation, DET-* rules |
| CI | GitHub Actions — lint, pytest (~333 test files), Windows job, security scan |
| Dashboard | NiceGUI (optional), Next.js `frontend/` scaffold |

Requirements traceability: [requirements.md](docs/requirements.md)

---

## Repository Structure

```text
windows_network_toolkit/   Primary CLI — proxy-status, diagnose, governance-report
src/platform_core/         Policy, evidence tiers, hash-chained audit, governance envelope
src/proxy_drift/           Startup observability, guardian, operator incident card
src/purple_team/           Fixture-driven control validation pipeline
src/proxy_guard/           Gated remediation, verification, snapshots
riskclaw/                  Agent contracts, skill loader, policy adapter
backend/                   FastAPI /trisk/*, /platform/*
scenarios/                 Purple scenario YAML (5 scenarios)
tests/                     Safety contracts, fixtures, purple, platform
docs/                      Enterprise + architecture + runbooks
```

Contributor rules: [AGENTS.md](AGENTS.md)

---

## Installation

```powershell
git clone https://github.com/Kozphy/Windows-Network-Recovery-Toolkit.git
cd Windows-Network-Recovery-Toolkit
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
$env:PYTHONPATH = (Get-Location).Path
pytest -q tests/test_policy_safety_contract.py tests/test_audit_contract.py
```

Docker reviewer demo: [docker-demo.md](docs/docker-demo.md) · Onboarding: [ONBOARDING.md](docs/ONBOARDING.md)

---

## Usage

### Read-only (recommended first)

```powershell
python -m windows_network_toolkit version
python -m windows_network_toolkit proxy-status --fixture examples/evidence/DEAD_PROXY_CONFIG.json
python -m windows_network_toolkit diagnose --proof --fixture examples/evidence/DEAD_PROXY_CONFIG.json
python -m windows_network_toolkit control-test --fixture tests/fixtures/case_studies/case_1_dead_wininet_proxy.json
python -m windows_network_toolkit governance-report --audit-dir tests/fixtures/risk_analytics/audit_sample --format markdown
```

### Gated remediation (Windows, explicit confirmation)

```powershell
python -m windows_network_toolkit proxy-disable --dry-run true          # preview (default)
python -m windows_network_toolkit proxy-disable --dry-run false --confirm DISABLE_WININET_PROXY
```

### Extended operator CLI (Windows)

```powershell
python -m src operator-incident --fixture tests/fixtures/operator_incident/ipv6_broken.json
python -m src collect-evidence-bundle
python -m src install-startup-observability --json
```

Runbooks: [dead-proxy-guardian.md](docs/dead-proxy-guardian.md) · [startup-observability.md](docs/startup-observability.md) · Full CLI: [cli_reference.md](docs/cli_reference.md)

### Purple Team

```powershell
python -m src.purple_team scenarios list
python -m src.purple_team validate proxy-drift-001
python -m src.purple_team run proxy-drift-001 --dry-run
python -m src.purple_team benchmark --no-evidence --json
```

### FastAPI (read-only technology risk API)

```powershell
uvicorn backend.main:app --reload
# GET /trisk/health · /incidents · /controls · /reports/executive
```

---

## Testing

```powershell
pytest -q tests/test_policy_safety_contract.py      # policy gates
pytest -q tests/test_audit_contract.py              # custody contracts
pytest -q tests/purple_team                           # purple pipeline
pytest -q tests/test_public_release_audit.py
make principles-test                                  # epistemic principles
```

CI: [.github/workflows/ci.yml](.github/workflows/ci.yml) · Strategy: [test-strategy.md](docs/test-strategy.md) · UAT: [uat-plan.md](docs/uat-plan.md)

---

## Empirical Evaluation

Controlled benchmark **dataset v1** (22 cases: 17 development, 5 held-out) compares four baselines from [RESEARCH.md](RESEARCH.md):

| Baseline | Description |
|----------|-------------|
| **B0** | Connectivity / probe signals only |
| **B1** | Flat if/else rules (no proof tiers or aggregation) |
| **B2** | WinINET `proxy_state` single-signal |
| **B3** | Full platform: evidence → proof tier → classification → policy |

**Headline metrics (dataset v1, all cases)** — source: [`experiments/results/latest/metrics.csv`](experiments/results/latest/metrics.csv), Git `95bad4ce`, cases digest `540a434d…`:

| Baseline | Accuracy | Macro F1 | Abstention rate |
|----------|----------|----------|-----------------|
| B0 | 0.1364 | 0.0868 | 0.6818 |
| B1 | 0.4545 | 0.4233 | 0.0000 |
| B2 | 0.1364 | 0.0583 | 0.4091 |
| **B3** | **0.6364** | **0.5852** | 0.3636 |

B3 macro F1 bootstrap 95% CI: **0.4464–0.7619** ([`benchmarks/statistical_summary.csv`](benchmarks/statistical_summary.csv)).

| Claim | Artifact |
|-------|----------|
| Ablation deltas | [`benchmarks/ablations.csv`](benchmarks/ablations.csv) |
| B3 failure taxonomy | [`benchmarks/error_analysis.csv`](benchmarks/error_analysis.csv) |
| Full report | [`docs/research/TECHNICAL_REPORT.md`](docs/research/TECHNICAL_REPORT.md) |
| Claims matrix | [`docs/research/CLAIMS_EVIDENCE_MATRIX.md`](docs/research/CLAIMS_EVIDENCE_MATRIX.md) |
| Failure analysis | [`docs/research/FAILURE_ANALYSIS.md`](docs/research/FAILURE_ANALYSIS.md) |
| Validity limits | [`docs/threats-to-validity.md`](docs/threats-to-validity.md) |
| Reproduce | [`REPRODUCING.md`](REPRODUCING.md) |
| **Visualization** | [`benchmarks/reports/research_dashboard.html`](benchmarks/reports/research_dashboard.html) · [Power BI template](analytics/powerbi/research/README.md) |

**Reproduce:**

```powershell
./scripts/reproduce.ps1
# or
make research
# Viz only: python -m experiments.viz --open
```

CI runs a fast smoke subset via `tests/experiments/` and `python -m experiments.run_benchmark --smoke`.

**Phase 1 — Interaction effects** (factorial fault designs): `make research-interactions` → [`experiments/results/interaction_effects.csv`](experiments/results/interaction_effects.csv) · [`docs/research/interaction_effects.md`](docs/research/interaction_effects.md)

---

## Demo

**Golden case:** Dead WinINET proxy `127.0.0.1:59081` — fixture-safe on any OS.

```powershell
python -m windows_network_toolkit proxy-status --fixture examples/evidence/DEAD_PROXY_CONFIG.json
python -m windows_network_toolkit proxy-health --fixture examples/evidence/DEAD_PROXY_CONFIG.json --json
python -m windows_network_toolkit diagnose --proof --fixture examples/evidence/DEAD_PROXY_CONFIG.json
```

3-minute panel paths: [interview-demo-3min.md](docs/interview-demo-3min.md) · Case pack: [real_evidence/case-001-dead-proxy/](real_evidence/case-001-dead-proxy/) · Reviewer demo: `python -m windows_network_toolkit reviewer-demo --mode mixed`

---

## Current Capabilities

| Capability | Status |
|------------|--------|
| Proxy/network evidence collection | **Implemented** |
| Classification + `limitations[]` + proof tiers | **Implemented** |
| Control tests CTRL-001–010 | **Implemented** |
| Policy-gated remediation preview | **Implemented** |
| Typed confirmation apply (WinINET disable) | **Implemented** |
| Post-apply verification | **Implemented** |
| Hash-chained audit + tip verify | **Implemented** |
| Purple Team validation loop | **Prototype** (fixture-first) |
| Governance / Power BI export | **Prototype** |
| Fleet signed agent | **Planned / not supported** |
| Formal regulatory attestation | **Not supported** |

Purple + Blue details: [purple-team-upgrade-report.md](docs/purple-team-upgrade-report.md)

---

## Limitations

- **Not** antivirus, EDR, XDR, or malware attribution
- **Not** autonomous remediation — dry-run default; typed tokens for apply
- **Not** formal audit opinions — management information only
- Writer proof requires optional Sysmon E13 — not bundled
- Confidence is ordinal — not calibrated probability
- Local audit chain ≠ WORM immutability
- Power BI = export blueprint, not deployed tenant

Non-claims enforced in CI. Gap table: [production-readiness-gap.md](docs/production-readiness-gap.md)

---

## Roadmap

| Priority | Item |
|----------|------|
| **P0** | Signed fleet agent; production API auth/RBAC |
| **P1** | Central custody / SIEM integration; fleet KPI warehouse |
| **P1** | Purple lab with rollback-proof live mutation |
| **P2** | ETW ingestion (stub today); browser repair apply (blocked) |
| **P3** | Operator NiceGUI console |

Hardening phases: [enterprise-hardening-roadmap.md](docs/enterprise-hardening-roadmap.md)

---

## Safety boundaries

| Allowed by default | Blocked without explicit human confirmation |
|--------------------|---------------------------------------------|
| Read registry / netstat | Registry mutation |
| Classify & prove | Process kill |
| Preview remediation | Firewall reset |
| Append audit logs | Adapter disable |
| Fixture replay | Autonomous remediation |

See [safety-model.md](docs/safety-model.md) · [SECURITY.md](SECURITY.md)

---

## Reviewer quick links

| Audience | Start here |
|----------|------------|
| **Hiring manager / Risk** | [case-study.md](docs/case-study.md), [executive-summary.md](docs/executive-summary.md) |
| **Big 4 / Audit** | [control-matrix.md](docs/control-matrix.md), [big4-interview-defense.md](docs/big4-interview-defense.md) |
| **Platform / SRE** | [faang-platform-review.md](docs/faang-platform-review.md), [replay-demo.md](docs/replay-demo.md) |
| **Engineer** | [DOCUMENTATION_INDEX.md](docs/DOCUMENTATION_INDEX.md), [AGENTS.md](AGENTS.md) |

---

## License

AGPL-3.0-only — see [LICENSE](LICENSE).

---

## Extended operator reference

Detailed proxy drift commands, localhost diagnose, dashboard, analytics pipeline, and troubleshooting patterns:

- [docs/TROUBLESHOOTING_PROXY.md](docs/TROUBLESHOOTING_PROXY.md)
- [docs/cli_reference.md](docs/cli_reference.md)
- [docs/localhost-diagnose.md](docs/localhost-diagnose.md)
- [docs/proxy-state-transitions.md](docs/proxy-state-transitions.md)

Evidence-to-analytics pipeline: [docs/architecture-infographic.md](docs/architecture-infographic.md) · Sample outputs: [examples/evidence/](examples/evidence/)
