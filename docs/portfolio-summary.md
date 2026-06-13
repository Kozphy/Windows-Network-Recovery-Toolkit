# Portfolio Summary — Windows Endpoint Network Reliability Toolkit

Use this document for LinkedIn, resume, cover letters, and interview preparation.

---

## One-liner

Evidence-based Windows endpoint network reliability and IT risk toolkit that diagnoses browser connectivity failures, WinINET proxy drift, unknown local proxy listeners, and endpoint reliability risks using a structured evidence chain — with policy-gated remediation and append-only audit.

---

## Problem

Corporate endpoints often fail in confusing ways: ping works, DNS works, but browsers break. Root causes frequently involve **WinINET proxy misconfiguration**, **dead localhost listeners**, or **unclassified local proxy processes** — not upstream network outages. Traditional fix scripts mutate registry state without evidence tiers, audit trails, or rollback — creating operational and compliance risk.

---

## What I Built

A Python 3.11+ **endpoint reliability decision platform** with:

- JSON-first CLI (`python -m windows_network_toolkit`)
- 12-primary proxy risk classifications
- Evidence tier state machine (observation → correlation → proof)
- Structured proof engine (listener check, WinINET/WinHTTP contrast, TLS path)
- Policy engine blocking destructive actions by default
- Dry-run remediation preview with typed confirmation tokens
- Append-only audit JSONL with replay and hash-chain verification
- FastAPI platform API and optional dashboard
- 1000+ pytest cases including safety contract tests
- GitHub Actions CI: lint, test, security scan (bandit, pip-audit, Trivy)

**Golden demo case:** dead WinINET proxy `127.0.0.1:59081` — fixture-safe on any OS.

---

## Why It Matters

| Stakeholder | Value |
|-------------|-------|
| IT support | Faster, consistent proxy triage |
| Endpoint reliability engineers | Deterministic replay and metrics hooks |
| Security analysts | Listener vs writer separation; no false certainty |
| Risk consultants | Audit-ready reports with limitations |
| Platform/SRE candidates | CI contracts, observability, decision infrastructure |

---

## Technical Skills Demonstrated

- Python platform design (collectors, facades, canonical core separation)
- Windows endpoint internals (WinINET, WinHTTP, registry, netstat attribution)
- Evidence modeling and epistemic guard patterns
- Policy-as-code and remediation allowlists
- FastAPI, Pydantic v2, Prometheus metrics
- pytest contract testing and fixture-based cross-platform CI
- Docker, GitHub Actions, security scanning
- Append-only audit logs and deterministic replay

---

## Business Skills Demonstrated

- IT risk framing with careful language (indicates / suggests / requires validation)
- Operational playbook design for L1/L2/L3 handoffs
- Case study documentation for workshops and interviews
- Honest limitation disclosure in client-facing outputs
- Big 4–style control mapping (identify, detect, respond, recover, govern)

---

## Risk Thinking Demonstrated

| Principle | Implementation |
|-----------|----------------|
| Observation ≠ Proof | Evidence tier guards; proof envelope before remediation |
| Correlation ≠ Causation | Listener match ≠ registry writer without Sysmon E13 |
| Confidence ≠ Certainty | Ordinal 0–1 scores with `limitations[]` |
| Policy Permission ≠ Safety Guarantee | Confirmation + rollback + audit still required |

---

## Interview Pitch

> "I built an endpoint reliability toolkit for Windows proxy failures — the case where ping works but browsers don't. It collects registry, listener, and path evidence, classifies risk across twelve categories, runs structured proof checks, and only then previews remediation behind policy gates. It never silently kills processes or resets firewall rules. Every output includes what we cannot prove. It's designed for IT support triage, security review, and audit replay — not as a replacement for EDR."

**30-second version:**
> "Evidence-first Windows proxy diagnostics with policy-gated fixes and audit replay."

---

## Resume Bullet Points

- Designed and implemented a **Python endpoint reliability platform** diagnosing WinINET proxy drift, localhost listener attribution, and TLS path anomalies with **12-label risk classification** and structured proof envelopes
- Enforced **safety contracts** via pytest and CI: dry-run default, blocked destructive actions (process kill, firewall reset, adapter disable), typed confirmation for registry mutations
- Built **append-only audit pipeline** (JSONL + hash-chain verification) enabling deterministic incident replay for SRE postmortems and IT risk review
- Delivered **JSON-first CLI and FastAPI platform** with 1000+ tests, GitHub Actions (lint/test/security), and fixture-based demos runnable without Administrator privileges
- Authored **case studies and consulting-style reports** separating observation, hypothesis, proof, and policy for Big 4 cyber risk and platform engineering audiences

---

## Quick Links

| Resource | Path |
|----------|------|
| README | [../README.md](../README.md) |
| Case study: proxy drift | [case-study-1-proxy-drift.md](case-study-1-proxy-drift.md) |
| Case study: unknown listener | [case-study-2-unknown-local-proxy-listener.md](case-study-2-unknown-local-proxy-listener.md) |
| Case study: decision engine | [case-study-3-endpoint-reliability-decision-engine.md](case-study-3-endpoint-reliability-decision-engine.md) |
| Demo script | [demo-video-script.md](demo-video-script.md) |
| Consulting report | [consulting-report.md](consulting-report.md) |
| Big 4 positioning | [big4-cyber-risk-positioning.md](big4-cyber-risk-positioning.md) |
