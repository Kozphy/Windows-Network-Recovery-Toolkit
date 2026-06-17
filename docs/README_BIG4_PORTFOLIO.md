# Technology Risk & Control Analytics Platform — Big 4 Portfolio Pack

Interview-ready materials for **IT Risk Advisory**, **Technology Consulting**, **Cyber / Technology Risk**, **Internal Audit**, **FinTech operational risk**, and **Platform/SRE governance** roles.

---

## One-line pitch

**Built a Technology Risk & Control Analytics Platform that transforms endpoint reliability incidents into evidence-backed risk assessments, control tests, remediation previews, audit trails, and governance reports.**

---

## Start here

| Document | Use when |
|----------|----------|
| [big4_interview_positioning.md](big4_interview_positioning.md) | Core framing, disclaimers, Big 4 mapping |
| [technology_risk_control_matrix.md](technology_risk_control_matrix.md) | Control testing workshop / whiteboard |
| [interview_pitch_90_seconds.md](interview_pitch_90_seconds.md) | Phone screen / recruiter call |
| [interview_pitch_5_minutes.md](interview_pitch_5_minutes.md) | Hiring manager / case interview |
| [big4_demo_flow.md](big4_demo_flow.md) | Live 5-minute demo script |
| [big4_interviewer_q_and_a.md](big4_interviewer_q_and_a.md) | Anticipated Q&A |
| [resume_bullets_big4.md](resume_bullets_big4.md) | Resume and LinkedIn About |
| [consulting_case_study.md](consulting_case_study.md) | STAR consulting narrative |
| [fintech_operational_risk_case.md](fintech_operational_risk_case.md) | FinTech / operational resilience angle |
| [linkedin_big4_portfolio_post.md](linkedin_big4_portfolio_post.md) | Public portfolio announcement |
| [analytics_data_model.md](analytics_data_model.md) | SQL warehouse schema for Data / Risk Analyst roles |
| [sql_analytics_queries.md](sql_analytics_queries.md) | 12+ analyst KPI queries with business interpretation |

**Related technical docs:** [big4-cyber-risk-positioning.md](big4-cyber-risk-positioning.md) · [consulting-report.md](consulting-report.md) · [interview-case-study.md](interview-case-study.md) · [safety_model.md](safety_model.md)

---

## What this is (and is not)

| Is | Is not |
|----|--------|
| Decision infrastructure for technology risk | Antivirus, EDR, or XDR |
| Evidence → hypothesis → proof → policy → audit | Autonomous remediation |
| Control testing and governance reporting | Malware verdict engine |
| Audit-ready JSONL with replay | Claim of final causation without telemetry |

**Core principles:** Observation ≠ Proof · Correlation ≠ Causation · Confidence ≠ Certainty · Policy Permission ≠ Safety Guarantee

---

## 5-minute demo (fixture-safe)

```powershell
pip install -e ".[dev]"
$env:PYTHONPATH = (Get-Location).Path

python -m windows_network_toolkit proxy-status --fixture tests/fixtures/enert/dead_proxy_59081.json
python -m windows_network_toolkit diagnose --proof --fixture tests/fixtures/enert/dead_proxy_59081.json
python -m windows_network_toolkit risk-assess --fixture tests/fixtures/case_studies/case_1_dead_wininet_proxy.json
python -m windows_network_toolkit control-test --fixture tests/fixtures/case_studies/case_1_dead_wininet_proxy.json
python -m windows_network_toolkit governance-report --fixture tests/fixtures/case_studies/case_1_dead_wininet_proxy.json --format markdown
python -m windows_network_toolkit proxy-disable --dry-run
```

Full script: [big4_demo_flow.md](big4_demo_flow.md)

---

## Consulting workflow frame

```text
Business Objective → Asset → Threat → Control → Testing → Finding → Risk Rating → Remediation → Governance
```

Implemented in `src/platform_core/risk/` and exposed via `risk-assess`, `control-test`, and `governance-report` CLI commands.

---

## Data Analyst / Risk Analytics layer

For **US Data Analyst**, **Risk Data Analyst**, and **Technology Risk Analyst** interviews:

| Resource | Purpose |
|----------|---------|
| [analytics_data_model.md](analytics_data_model.md) | Warehouse ER model, DDL, ETL mapping, example rows |
| [sql_analytics_queries.md](sql_analytics_queries.md) | 12+ KPI queries with business questions |
| [`schemas/analytics_warehouse.sql`](../schemas/analytics_warehouse.sql) | Executable DDL |
| [`schemas/analytics_seed.sql`](../schemas/analytics_seed.sql) | Sample rows for local SQL demos |

```powershell
sqlite3 analytics_demo.db < schemas/analytics_warehouse.sql
sqlite3 analytics_demo.db < schemas/analytics_seed.sql
```

**Interview angle:** Bridge engineering JSON (`proxy-status`, `risk-assess`) to management KPIs — evidence maturity %, policy block rate, preview-only remediation ratio — without collapsing observation into proof.
