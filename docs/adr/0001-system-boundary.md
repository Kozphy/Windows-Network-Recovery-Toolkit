# ADR-0001: System Boundary

**Status:** Accepted
**Date:** 2026-08-31
**Related:** [system-boundary.md](../system-boundary.md) · [0001-evidence-to-action-pipeline.md](0001-evidence-to-action-pipeline.md)

---

## Context

The repository began as a Windows network recovery toolkit and evolved into a **Technology Risk & Control Analytics Platform** with Blue Team diagnostics and Purple Team control validation.

Stakeholders (IT Ops, Security, Risk, Audit) need clarity on:

- What problems the system solves
- What decisions it enables
- What it must **never** autonomously do

Without an explicit boundary, portfolio reviewers may misclassify the project as EDR, autonomous remediation, or regulatory attestation software — all **unsupported**.

---

## Decision

The system boundary is defined as:

**In scope:** Local-first collection of Windows endpoint proxy/network evidence; deterministic classification with limitations; control testing; policy-gated remediation **previews**; hash-chained audit; fixture-driven purple control validation.

**Out of scope:** Malware detection; autonomous high-risk mutation; formal audit opinions; fleet-signed agent at scale; WORM/SIEM custody; production OAuth/RBAC.

Automation defaults:

| Class | Default |
|-------|---------|
| Read-only evidence | Automated |
| Classification | Automated with human review for ambiguous labels |
| Remediation apply | Human confirmation + typed token |
| Purple CI runs | Fixture simulate only |

---

## Alternatives considered

### A — Full EDR-style security product

**Benefits:** Broader market narrative
**Costs:** Unsupported claims; competes with entrenched vendors; requires kernel telemetry
**Rejected:** Violates epistemic boundaries and existing non-claims

### B — Autonomous self-healing endpoint agent

**Benefits:** Lower MTTR in theory
**Costs:** High blast radius; audit and approval gaps
**Rejected:** Conflicts with ADR-0002 policy-gated remediation

### C — Documentation-only portfolio (no working gates)

**Benefits:** Faster README polish
**Costs:** Fails engineering credibility review
**Rejected:** Working policy gates and CI contracts are core value

### D — Chosen: Decision-support platform with explicit gates (this ADR)

**Benefits:** Honest positioning; testable safety contracts; audit trail
**Costs:** Requires operators to confirm applies; not "one-click fix"

---

## Trade-offs

| Gain | Sacrifice |
|------|-----------|
| Audit defensibility | Speed of ungated scripts |
| Cross-platform CI via fixtures | Live Windows-only apply testing burden |
| Non-accusatory triage | Cannot satisfy "find the attacker" narratives |

---

## Consequences

**Positive:**

- README and enterprise docs can cite consistent boundary
- CI safety contracts align with boundary
- Hiring managers see judgment, not buzzwords

**Negative:**

- Cannot claim enterprise fleet deployment without additional work ([production-readiness-gap.md](../production-readiness-gap.md))
- Security buyers expecting EDR will need explicit redirect

---

## Conditions for revisiting

Change this ADR when:

1. Signed fleet agent + centralized custody ship with tests
2. Production RBAC/OAuth is implemented (not demo headers)
3. Purple Team gains lab-gated live mutation with proven rollback

Until then, portfolio title remains **Technology Risk & Control Analytics Platform**, not "Autonomous Endpoint Security."
