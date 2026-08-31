# Portfolio Summary

Use for GitHub, resume, LinkedIn, and interviews.
**Full case study:** [case-study.md](case-study.md) · **Executive summary:** [executive-summary.md](executive-summary.md)

> Independently developed enterprise-style reference implementation — not claimed as production deployment at a named institution.

---

## Recommended positioning

**Portfolio title:** Technology Risk & Control Analytics Platform (Windows Endpoint Reliability & Control Validation)
**Repository name:** Windows Network Recovery Toolkit (kept for continuity and SEO)
**One sentence:** Converts Windows endpoint proxy/network telemetry into control evidence, policy-gated remediation decisions, and hash-chained audit records — with fixture-driven control validation.

---

## GitHub (100–150 words)

Enterprise Windows endpoints often drift from approved network baselines—dead localhost proxies, WinINET/WinHTTP mismatches—causing browser failures and weak audit trails when teams reset registry settings ad hoc. This platform collects structured evidence, classifies incidents with explicit limitations and proof tiers, runs deterministic control tests (CTRL-001–010), and gates remediation behind policy and typed confirmation (dry-run by default). Hash-chained JSONL custody supports tamper detection; a Purple Team module validates detection quality via fixture-driven simulate→detect→verify→measure loops. Built in Python with ~333 pytest files, CI safety contracts, and FastAPI read APIs. Not EDR/AV; not autonomous remediation; designed to support control evidence generation for IT Ops, Security, Risk, and Audit stakeholders.

---

## Resume (one entry, bullets)

**Technology Risk & Control Analytics Platform** — Python, Windows internals, FastAPI, GitHub Actions

- Built evidence-to-decision pipeline for Windows proxy drift: collectors, ordinal classifiers with `limitations[]`, CTRL-001–010 control tests, and policy-gated remediation previews (dry-run default + confirmation tokens).
- Implemented hash-chained audit custody with tip verification and governance envelope separating claim strength from execution authority.
- Added fixture-driven Purple Team validation (scenarios, detection rules, benchmarks) with deny-by-default safety gate; CI enforces replay determinism and safety contracts.

---

## LinkedIn (100–200 words)

I designed and built a Technology Risk & Control Analytics Platform that addresses a common enterprise gap: endpoints look "online" while browsers fail due to proxy configuration drift—not datacenter outages.

The system converts operational signals into auditable decisions. It collects WinINET/WinHTTP evidence, classifies reliability incidents without false malware verdicts, runs mapped control tests, and produces remediation previews before any registry change. Policy gates and typed confirmation tokens enforce human authorization; hash-chained JSONL records support custody verification.

A Purple Team overlay measures control validation quality through deterministic scenarios (simulate, detect, respond, verify, benchmark)—safe for CI, not stealth tooling.

This is an independently developed reference implementation demonstrating enterprise architecture judgment: clear system boundaries, fail-safe failure handling, and testable governance—not buzzword automation. Stack: Python 3.11+, pytest safety contracts, FastAPI, Docker, GitHub Actions.

---

## Interview — 60 seconds

**Problem:** Enterprise browsers break when WinINET proxy settings drift; teams fix symptoms without evidence or audit trails.

**Decision:** Separate observation from proof; never auto-apply registry changes.

**System:** Evidence collectors → classification with limitations → control tests → policy-gated preview → optional confirmed apply → verification → hash-chained audit.

**Control:** Blocked destructive actions; CI safety contracts; purple fixture benchmarks for detection quality.

**Outcome:** Faster, defensible triage and committee-ready traceability—in design, not claimed as live ROI.

---

## Capability status (quick reference)

| Area | Status |
|------|--------|
| Proxy evidence + classification | Implemented |
| Policy-gated remediation preview | Implemented |
| Hash-chained audit | Implemented |
| Purple Team validation | Prototype (fixture-first) |
| Fleet signed agent | Planned / not supported |
| Formal regulatory attestation | Not supported |

---

## Links for reviewers

| Audience | Document |
|----------|----------|
| Executive | [executive-summary.md](executive-summary.md) |
| Risk / Audit | [control-matrix.md](control-matrix.md), [risk-register.md](risk-register.md) |
| Engineering | [architecture.md](architecture.md), [decision-model.md](decision-model.md) |
| Hiring manager | [case-study.md](case-study.md) |
