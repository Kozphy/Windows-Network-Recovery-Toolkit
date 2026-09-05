# Executive Summary

**Recommended portfolio title:** Technology Risk & Control Analytics Platform (Windows Endpoint Reliability & Control Validation)
**Repository:** Windows Network Recovery Toolkit
**Status:** Independently developed enterprise-style reference implementation — **not** production deployment at a named institution

---

## Situation

Enterprise Windows endpoints frequently exhibit a painful pattern: the network appears healthy (ping, DNS), yet browsers and line-of-business applications fail. A common root cause is **proxy configuration drift** — WinINET pointing at a dead localhost listener, WinINET/WinHTTP stack mismatch, or TLS path divergence — not upstream outage.

Teams respond with ad-hoc registry resets, inconsistent triage, and narratives that over-claim certainty. Audit and risk functions cannot easily answer: *What evidence supported the decision? Who authorized the change? Did verification confirm success?*

---

## Risk

| Risk domain | Impact if unaddressed |
|-------------|----------------------|
| **Operational** | Extended MTTR, repeat incidents, user productivity loss |
| **Control** | Undetected config drift; remediation without preview or rollback |
| **Security narrative** | False malware accusations from weak attribution |
| **Audit** | Non-replayable decisions; broken evidence chain |
| **Compliance process** | Changes without traceable approval |

This repository does **not** eliminate these risks. It **structures** detection, decision, and evidence generation so residual risk is visible and testable.

---

## System

A Python platform that:

1. **Collects** Windows proxy/network evidence (registry, listeners, probes, optional Sysmon).
2. **Classifies** incidents with explicit `limitations[]` and proof tiers (T0–T5).
3. **Tests** mapped controls (CTRL-001–010) with PASS/FAIL/PARTIAL outcomes.
4. **Gates** remediation behind policy and typed confirmation — **dry-run by default**.
5. **Verifies** post-conditions where implemented.
6. **Records** hash-chained audit events with optional tip anchor.
7. **Validates** controls via fixture-driven Purple Team scenarios (simulate → detect → verify → measure).

Dual mode: **Blue Team** reliability analytics (production-shaped prototype) + **Purple Team** control validation (fixture-first).

---

## Decision

Decisions that become **easier and safer**:

| Decision | How the system helps |
|----------|---------------------|
| Is this a dead proxy vs security incident? | Structured labels; no malware verdict by default |
| Should we reset registry settings? | Preview diff + rollback snapshot first |
| Did the control work? | Deterministic control tests + purple verification |
| Can we use this evidence in a committee pack? | Governance envelope + hash chain verify |
| Is automation allowed? | Policy outcome visible before any mutation |

---

## Control

Controls **designed to support evidence generation** (not regulatory certification):

| Control area | Example |
|--------------|---------|
| Configuration drift | CTRL-001 dead proxy detection |
| Stack alignment | CTRL-002 WinINET/WinHTTP |
| Safe remediation | CTRL-009 policy-gated preview |
| Audit integrity | CTRL-010 hash chain verification |
| Narrative discipline | CTRL-006 non-accusatory triage |

Full matrix: [control-matrix.md](control-matrix.md)

---

## Evidence

| Artifact | Purpose |
|----------|---------|
| Diagnose / proxy-status JSON | Point-in-time evidence bundle |
| Control test results | Control effectiveness signal |
| Remediation preview | Intended change before apply |
| `.audit/canonical_custody.jsonl` | Hash-chained decision trail |
| Governance report | Committee-ready management information |
| Purple evidence bundle | Control validation run record |

Audit verify: `python -m windows_network_toolkit audit verify .audit/canonical_custody.jsonl --check-tip`

---

## Outcome

**Intended organizational benefits** (measurable via [kpi-framework.md](kpi-framework.md) — no fabricated ROI):

- Shorter, more consistent diagnosis cycles
- Reduced unsafe registry mutation
- Clearer ownership between IT Ops, Security, and Risk
- Stronger traceability from signal → decision → action → verification
- Demonstrable control-test and purple-validation discipline for hiring and design reviews

---

## What this is not

- Not antivirus, EDR, XDR, or malware attribution
- Not autonomous remediation
- Not SOC 2 / ISO / PCI certified
- Not a formal audit opinion

---

## Audience quick links

| Reader | Next document |
|--------|---------------|
| CIO / CTO | [business-case.md](business-case.md) |
| CISO / Risk | [risk-register.md](risk-register.md), [control-matrix.md](control-matrix.md) |
| Audit | [audit-custody.md](audit-custody.md), [decision-model.md](decision-model.md) |
| Engineering | [architecture.md](architecture.md), [AGENTS.md](../AGENTS.md) |
| Hiring panel | [case-study.md](case-study.md), [portfolio-summary.md](portfolio-summary.md) |
