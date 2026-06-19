# Portfolio: AI-Assisted Technology Risk & Control Analytics Platform

This project demonstrates how **endpoint reliability evidence** can be converted into **technology risk decisions**. It diagnoses proxy drift and TLS path issues, classifies incidents with proof tiers, blocks unsafe remediation by default, and generates audit-ready governance reports with replay verification.

## Project title

**Technology Risk & Control Analytics Platform** — evidence-backed endpoint reliability decision infrastructure with AI-assisted explanation and governance reporting.

---

## Target roles

- Technology Risk Analyst  
- Cyber Risk Consultant  
- IT Audit / IT Risk Advisory  
- AI Application Engineer (governance-first assistants)  
- Data / Risk Analyst  
- Platform / Endpoint Reliability Analyst  

---

## Problem solved

Organizations lose time when endpoint network failures (proxy drift, WinINET/WinHTTP mismatch, dead localhost listeners) create **disagreement** between IT Support, Security, Compliance, and Audit:

- Helpdesk resets settings without evidence  
- Security suspects compromise without proof tier  
- Audit cannot reconstruct decisions  
- Risk committees lack KPIs from incident data  

This platform standardizes **Evidence → Risk → Decision → Audit** with policy-gated remediation previews.

---

## Technical stack

| Layer | Technology |
|-------|------------|
| Core engine | Python 3.11+, Pydantic v2 |
| CLI | `windows_network_toolkit`, `python -m src` |
| API | FastAPI, OpenAPI |
| Audit | Append-only hash-chained JSONL |
| CI/CD | GitHub Actions (lint, test, typecheck, Docker build) |
| Frontend (optional) | Next.js operator console |
| AI (advisory) | Rule-based analyst + optional LLM provider abstraction |

---

## Risk / governance relevance

- Maps to **technology risk** and **IT general controls** framing (change management, logging, access)  
- **Control tests** with PASS/FAIL/INSUFFICIENT_EVIDENCE  
- **Risk ratings** with explicit limitations (not regulatory attestation)  
- **Framework mapping** docs for NIST CSF / ISO 27001 language (see `docs/framework_mapping.md`)  
- Six epistemic principles: observation ≠ proof, correlation ≠ causation, etc.  

---

## What this deliberately does not solve

Not antivirus, EDR, autonomous remediation, malware verdicts, guaranteed MITM detection, regulatory certification, or AI-authorized execution.

**Defense against “AI code paste”:** [docs/anti-code-paste-defense.md](docs/anti-code-paste-defense.md)

**Production prototype pack:** [real_evidence/case-001-dead-proxy/](real_evidence/case-001-dead-proxy/) · [docs/production-readiness-gap.md](docs/production-readiness-gap.md) · [docs/threat-model.md](docs/threat-model.md) · [docs/docker-demo.md](docs/docker-demo.md) · `reviewer-demo` · `fleet-simulate`

**FAANG + Big 4 demo:** [docs/demo-faang-big4-review.md](docs/demo-faang-big4-review.md)

---

| Theme | Demonstration in this repo |
|-------|---------------------------|
| Evidence-based diagnosis | `proxy-status`, `diagnose --proof`, proof tiers T0–T4 |
| Control testing | `control-test` mature records per classification |
| Policy-gated automation | Preview-only remediation, typed confirmation |
| Auditability | Hash-chained JSONL, `audit verify`, governance appendix |
| Human-in-the-loop | `RiskDecisionRecord`, human-review queue in reports |
| Responsible AI | `ai_risk_analyst` guardrails + report transparency section |
| Platform discipline | 1200+ tests, fixture replay, CI safety contracts |

---

## What I personally learned

- How to separate **triage classification** from **security verdicts**  
- Designing **policy gates** that default to preview, not execution  
- Building **audit trails** that survive interview scrutiny  
- Using AI for **documentation and test ideas** while keeping decisions evidence-backed  
- Portfolio storytelling for **risk consulting** vs **pure SRE** audiences  

---

## Interview pitch (60 seconds)

> I built a Technology Risk & Control Analytics Platform for Windows endpoint reliability. When browsers fail but ping works, teams often blame the network or assume malware. This system collects WinINET and WinHTTP evidence, classifies proxy drift, runs proof contrasts, rates risk, and produces audit-ready governance reports — with remediation locked behind typed confirmation. AI assists explanation and report drafting, but final decisions stay evidence-backed. It's decision infrastructure, not EDR or autonomous remediation.

---

## Resume bullet points

- Built an evidence-to-action platform transforming endpoint proxy incidents into risk assessments, control tests, and hash-chained audit trails  
- Implemented policy-gated remediation previews with six epistemic governance principles and ordinal confidence (not false precision)  
- Delivered CLI + FastAPI surfaces for proxy classification, TLS proof, governance reports, and risk KPI analytics  
- Established CI safety contracts: dry-run defaults, no silent destructive actions, deterministic fixture replay  
- Authored portfolio documentation, demo scripts, and sample evidence packs for technology risk and cyber consulting interviews  

---

## Power BI / PL-300 Portfolio Evidence

| Topic | Artifact |
|-------|----------|
| **Dataset prepared** | Star schema CSVs via `powerbi-export` — [examples/powerbi/export/](examples/powerbi/export/) |
| **Star schema designed** | `fact_incidents`, `fact_control_tests`, `fact_policy_decisions` + `dim_*` tables |
| **DAX measures defined** | Total Incidents, Control Failure Rate, Security Accusation Count (expect 0), etc. — [dax/measures.md](examples/powerbi/dax/measures.md) |
| **Dashboard pages specified** | Executive · Control Effectiveness · Policy Gate · Proof Tier — [report_blueprint.md](examples/powerbi/report_blueprint.md) |
| **RLS design** | IT Support, Security, Audit, Risk Committee roles — [rls_design.md](examples/powerbi/rls_design.md) |
| **Technology Risk → business reporting** | Connects endpoint reliability evidence to committee KPIs without malware accusation language |

```powershell
python -m windows_network_toolkit powerbi-export `
  --audit-dir tests/fixtures/risk_analytics/audit_sample `
  --out-dir examples/powerbi/export
```

**Interview angle:** “I built the governance engine in Python, exported a star schema for Power BI, and designed DAX KPIs plus RLS roles so technology risk evidence reaches executives with preview-only safety boundaries.”

---

## Quick demo

```powershell
pip install -e ".[dev]"
$env:PYTHONPATH = (Get-Location).Path
python -m windows_network_toolkit proxy-status --fixture examples/evidence/DEAD_PROXY_CONFIG.json
python -m windows_network_toolkit risk-assess --fixture tests/fixtures/case_studies/case_1_dead_wininet_proxy.json
python -m windows_network_toolkit governance-report --audit-dir tests/fixtures/risk_analytics/audit_sample --format markdown
```

Full walkthrough: [docs/demo-script.md](docs/demo-script.md)

---

## Key artifacts

| Artifact | Path |
|----------|------|
| Architecture | [docs/architecture.md](docs/architecture.md) |
| AI delivery notes | [docs/ai-assisted-delivery.md](docs/ai-assisted-delivery.md) |
| Sample evidence | [examples/evidence/](examples/evidence/) |
| Sample reports | [examples/reports/](examples/reports/) |
| Case study | [docs/portfolio-case-study-1-dead-wininet-proxy.md](docs/portfolio-case-study-1-dead-wininet-proxy.md) |
| Case study 2 | [docs/portfolio-case-study-2-wininet-winhttp-mismatch.md](docs/portfolio-case-study-2-wininet-winhttp-mismatch.md) |
| Case study 3 | [docs/portfolio-case-study-3-reverter-suspected.md](docs/portfolio-case-study-3-reverter-suspected.md) |
| Power BI layer | [examples/powerbi/](examples/powerbi/) · [analytics/powerbi/](analytics/powerbi/) |

---

## Disclaimer

This project is **not** antivirus, EDR, XDR, SIEM replacement, malware detection, or intrusion prevention. Heuristic and AI-assisted outputs support human review — they are not automated blocking verdicts.
