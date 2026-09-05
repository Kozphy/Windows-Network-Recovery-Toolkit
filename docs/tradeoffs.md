# Architecture Trade-offs

**Platform:** Technology Risk & Control Analytics for Windows endpoints
**Principle:** Good architecture chooses appropriate constraints — not maximum complexity

---

## T-001 — Local-first vs centralized SaaS

| | Option A: Local-first CLI + JSONL | Option B: Centralized multi-tenant SaaS |
|---|-----------------------------------|----------------------------------------|
| **Benefits** | No default data exfiltration; works offline; audit on device | Fleet dashboards; single pane of glass |
| **Costs** | Weak fleet rollup; manual export | OAuth, HA, data residency, ops burden |
| **Chosen** | **Option A** | |
| **Why** | Portfolio + ADR-005; privacy boundary for endpoint evidence |
| **Revisit when** | Signed agent + approved custody pipeline exists |

**Status:** **Implemented** (local-first)

---

## T-002 — Fixture-driven CI vs live Windows-only CI

| | Option A: Deterministic fixtures | Option B: Live registry mutation in CI |
|---|----------------------------------|----------------------------------------|
| **Benefits** | Cross-platform; replay; zero flake | Higher fidelity |
| **Costs** | Live drift not caught in Linux CI | Flaky; security risk in shared runners |
| **Chosen** | **Fixtures primary** + Windows zero-skip job | |
| **Why** | Safety contracts and replay determinism |
| **Revisit when** | Dedicated Windows lab with rollback snapshots |

**Status:** **Implemented**

---

## T-003 — Dry-run default vs one-click fix

| | Option A: Preview default | Option B: Auto-apply common fixes |
|---|----------------------------|-----------------------------------|
| **Benefits** | Audit-friendly; lower blast radius | Faster MTTR for experts |
| **Costs** | Extra operator step | Control failures; audit gaps |
| **Chosen** | **Option A** | |
| **Why** | CTRL-009; technology risk positioning |
| **Revisit when** | Org policy defines auto-apply allowlist with fleet proof |

**Status:** **Implemented**

---

## T-004 — Rule-based classification vs ML classifier

| | Option A: Deterministic rules + proof tiers | Option B: ML / LLM classifier |
|---|---------------------------------------------|-------------------------------|
| **Benefits** | Explainable; testable; CI regression | Handles noisy edge cases |
| **Costs** | Manual rule maintenance | False certainty; training data bias |
| **Chosen** | **Option A**; LLM explanation-only optional | |
| **Why** | Epistemic boundaries; no fabricated AI accuracy |
| **Revisit when** | Labeled fleet dataset + eval harness exists |

**Status:** **Implemented** (rules); AI **Prototype** (explanation only)

---

## T-005 — Hash-chained JSONL vs external WORM

| | Option A: Local hash chain + tip | Option B: SIEM / WORM storage |
|---|-----------------------------------|------------------------------|
| **Benefits** | Simple; verifiable offline | Stronger tamper resistance |
| **Costs** | Not immutable if attacker owns host | Infra cost; integration |
| **Chosen** | **Option A** for portfolio | |
| **Why** | Demonstrates custody thinking without fake enterprise infra |
| **Revisit when** | Production ships with signed remote anchor |

**Status:** **Implemented** (local)

---

## T-006 — Monolith Python platform vs microservices

| | Option A: Package monolith + optional API | Option B: Microservices per domain |
|---|---------------------------------------------|-------------------------------------|
| **Benefits** | Easier test; lower ops | Independent scale |
| **Costs** | Scale limits | Distributed complexity for portfolio |
| **Chosen** | **Option A** | |
| **Why** | Problem fits single-team codebase; ~333 test files |
| **Revisit when** | Fleet ingest exceeds single-process throughput |

**Status:** **Implemented**

---

## T-007 — Purple fixture simulation vs live adversary emulation

| | Option A: YAML + fixture simulate | Option B: Live offensive tooling |
|---|-------------------------------------|----------------------------------|
| **Benefits** | CI-safe; deterministic metrics | Realistic TTP coverage |
| **Costs** | Not real adversary behavior | Safety, legal, lab cost |
| **Chosen** | **Option A** in CI; lab token for live | |
| **Why** | Deny-by-default safety gate |
| **Revisit when** | Isolated lab with rollback proof |

**Status:** **Prototype**

---

## T-008 — NiceGUI / Next.js dashboard vs CLI-first

| | Option A: CLI + JSON + optional API | Option B: Dashboard-first product |
|---|---------------------------------------|-----------------------------------|
| **Benefits** | Scriptable; auditable; CI-friendly | Executive visibility |
| **Costs** | Less visual appeal | UI maintenance |
| **Chosen** | **Option A** primary; dashboards secondary | |
| **Why** | Evidence and audit originate at CLI |
| **Revisit when** | Operator persona requires single UI |

**Status:** CLI **Implemented**; dashboards **Prototype**

---

## Summary judgment

This repository optimizes for **defensible decisions and testable controls**, not for **feature count or infrastructure spectacle**. That is intentional for technology risk and platform engineering portfolio positioning.

See also: [production-readiness-gap.md](production-readiness-gap.md) for P0–P3 implementation gaps.
