# Case Study — Technology Risk & Control Analytics Platform

> **Disclosure:** This project is an **independently developed enterprise-style reference implementation / portfolio case study**. It is not claimed as production deployment at a named financial institution or client engagement.

---

## Context

Windows endpoints in enterprise environments often fail in ways that look like "network is down" but are actually **local proxy misconfiguration**: WinINET enabled toward a dead localhost port, WinINET/WinHTTP stack mismatch, or TLS path differences. IT teams spend hours on ad-hoc registry edits. Security teams face pressure to label incidents as compromise. Audit cannot reconstruct what evidence supported a reset.

I built this repository to demonstrate how to translate that ambiguous operational problem into a **measurable, controllable, testable, auditable** software system.

---

## Enterprise Problem

**Who experiences it:** IT Operations, endpoint support, security triage, internal audit sampling.

**Why it matters:** Connectivity failures reduce productivity; unsafe remediation creates control exceptions; weak evidence undermines risk committees and post-incident review.

**If nothing is done:** Repeat incidents, inconsistent fixes, false security escalations, non-replayable decisions.

---

## Constraints

- Must not present as EDR/AV or malware attribution
- Remediation must default to preview — no silent registry mutation
- Must run deterministic CI on Linux and full tests on Windows
- Must preserve epistemic boundaries (`limitations[]`, proof tiers)
- Portfolio scope — not funded fleet agent program

---

## My Role

Sole architect and implementer: requirements, policy model, collectors, classification, control tests, audit custody, Purple Team validation loop, CI safety contracts, and enterprise documentation.

---

## Analysis

**Current-state gap:** Tools either mutate settings without evidence (scripts) or detect threats without proxy drift specificity (EDR).

**Target state:** Separate Observation → Hypothesis → Proof → Policy → Remediation → Audit, with human gates on apply.

**Key insight:** Most "unknown proxy" incidents are **reliability and attribution** problems, not malware verdicts — language must reflect that.

---

## Key Architecture Decisions

| Decision | Rationale |
|----------|-----------|
| Local-first evidence + hash-chained JSONL | Audit defensibility without fake WORM ([tradeoffs.md](tradeoffs.md) T-005) |
| Policy engine + BLOCKED_ACTIONS registry | Fail closed on destructive ops ([0002-policy-gated-remediation.md](adr/0002-policy-gated-remediation.md)) |
| Fixture-driven purple CI | Safe control validation metrics ([purple_team/architecture.md](purple_team/architecture.md)) |
| Governance envelope on JSON outputs | Separates claim strength from execution authority |
| Dual CLI (`windows_network_toolkit` + `src`) | Operator vs extended observability without breaking backward compatibility |

---

## Implementation

**Blue Team path:**

```text
proxy-status / diagnose → classify → control tests → preview remediation → audit verify
```

**Purple Team path:**

```text
scenario YAML → safety gate → fixture sim → detect → respond (preview) → verify → benchmark
```

**Scale:** ~333 test files; hash-chained custody; 12+ classification labels; CTRL-001–010.

Golden demo: dead WinINET proxy `127.0.0.1:59081` via fixture (any OS).

---

## Controls

Designed to **support control evidence generation** — see [control-matrix.md](control-matrix.md):

- CTRL-001 dead proxy detection
- CTRL-009 policy-gated remediation
- CTRL-010 audit hash chain integrity
- CTRL-006 non-accusatory triage

Not claimed: SOC 2, ISO, or regulatory certification.

---

## Testing

- Safety contract tests in CI (policy, audit, replay, evidence level)
- Principle tests: observation ≠ proof, correlation ≠ causation
- Purple pipeline tests + benchmark smoke job
- Public-release hygiene scan

```powershell
pytest -q tests/test_policy_safety_contract.py tests/test_audit_contract.py tests/purple_team
python -m src.purple_team benchmark --no-evidence --json
```

---

## Failure Handling

Taxonomy F1–F9 ([failure-taxonomy.md](failure-taxonomy.md)): fail safe on policy/auth; soft-fail audit with documented limitation; verification failures block incident closure.

---

## Evidence

| Question | Where to look |
|----------|---------------|
| Who decided? | `.audit/canonical_custody.jsonl` |
| What evidence? | Diagnose JSON, control test results |
| Was chain intact? | `audit verify --check-tip` |
| Did control validation pass? | Purple benchmark metrics |

Confirmation **token values are not stored** — only `confirmation_supplied: true/false`.

---

## Results

**Demonstrable (not fabricated production metrics):**

- CI-enforced safety contracts and replay determinism
- End-to-end fixture demo from symptom to governance report
- Purple benchmark producing Precision/Recall/F1 on scenarios
- Hash-chain tamper detection tests passing

---

## Limitations

- No production fleet agent or centralized SIEM custody
- Writer proof requires optional Sysmon — not default
- Browser repair apply intentionally blocked
- Power BI is export blueprint, not deployed tenant
- Confidence scores are ordinal — not probabilities

Full gap table: [production-readiness-gap.md](production-readiness-gap.md)

---

## What I Would Change in Production

| Priority | Change |
|----------|--------|
| **P0** | Signed agent; OAuth/RBAC on API; mandatory verify before close |
| **P1** | Central custody with WORM or signed remote tip |
| **P1** | Fleet KPI warehouse from agent heartbeats |
| **P2** | Isolated purple lab with rollback proof for live mutation |
| **P3** | NiceGUI operator console for demo deployments |

---

## Interview prompt (60 seconds)

*"Enterprise browsers often break while the network looks fine — usually WinINET proxy drift. I built a platform that collects structured evidence, classifies incidents with explicit limitations, runs control tests, gates any registry change behind preview and typed confirmation, verifies outcomes, and writes hash-chained audit records. A purple validation layer measures detection quality on fixtures. It's a reference implementation showing how to turn operational risk into auditable decisions — not an EDR replacement."*

See also: [portfolio-summary.md](portfolio-summary.md)
