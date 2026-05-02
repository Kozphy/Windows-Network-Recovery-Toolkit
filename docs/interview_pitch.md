# Interview pitch (Failure Knowledge System)

Use this to explain the project as **platform-style** diagnostics—not “just scripts.”

---

## 30 seconds

> **Windows Network Recovery Toolkit** adds a **Failure Knowledge System** on top of Windows repair workflows: we collect read-only signals, normalize them into features, run a **deterministic** rule engine—no ML for core RCA—and emit **FailureBlocks** to append-only JSONL with clear risk and rollback text. Repairs never auto-run; operators confirm before any state change. It’s designed like internal SRE tooling: auditable, local-first, safety-bounded.

---

## 2 minutes

Home networks often show “connected” while DNS, proxy, or HTTPS paths fail. This repo **structures** the problem: **signal layer** (subprocess/registry probes), **feature layer** (`FeatureVector` / snapshots), **decision layer** (ranked hypotheses with explainable confidence-like scores), **knowledge layer** (typed FailureBlocks + JSONL), and **interface layer** (CLI, FastAPI, batch wrappers). A **control layer** keeps diagnosis and mutation separate—**Failure Knowledge System code never executes repair commands**; batch and confirmation-gated CLIs do.

Append-only JSONL gives an audit trail without shipping logs to a vendor by default. Optional folders (`backend/`, `frontend/`, `network_agent/`) show how the same ideas extend to HTTP and demos, but the **core product story** is local explainability and operator consent.

---

## Technical deep dive (talking points)

- **Deterministic scoring** — Easier to test (`tests/fixtures/`), reproduce incidents, and defend recommendations than black-box models for **local** repair hints.
- **Separation of knowledge vs execution** — FailureBlocks **describe**; `.bat` / policy-wrapped repair paths **mutate** after confirmation.
- **Risk as narrative tier** — `low` / `medium` / `high` describe the **suggested human action**, not packet loss SLOs.
- **Privacy-aware audit** — Truncated outputs; fingerprinted host keys in CLI audit paths (see `src/cli.py`) rather than raw hostnames where documented.

---

## Architecture (elevator diagram)

`Signals → Collectors → Features → RuleEngine → FailureBlock → JSONL → Search/API → (human) Repair`

---

## Tradeoffs (honest)

- **Coverage vs simplicity** — Heuristics won’t catch every enterprise policy edge case; the win is **explainability** and **fast local iteration**.
- **Token search vs semantic search** — Current FailureBlock search is intentionally simple; ranking improvements are incremental, not magic.
- **Optional demo stack** — SaaS-style folders exist for portfolio demos; they are **not** required to use the Failure Knowledge System core.

---

## What this demonstrates (Backend / Platform / SRE)

- Designing **safe automation boundaries** (read-only diagnostics vs confirmed repair).
- **Structured operational data** (typed records, append-only logs, JSON APIs).
- **Testable decision logic** and fixture-driven regression.
- **Operational clarity** for on-call style workflows without mandatory cloud telemetry.

---

## What not to claim

- Not “AI-driven automatic repair.”
- Not “uploads logs for training” — default posture is **local** artifacts; demos require explicit configuration.
- Not a substitute for enterprise NMS or MDM—scope is **single-machine Windows** diagnostics and operator-guided repair.
