# Business Case

**Platform:** Technology Risk & Control Analytics for Windows endpoints
**Status:** Reference implementation — benefits are **intended** and **measurable**, not claimed as achieved ROI

---

## Problem

Enterprise endpoints drift from approved network baselines. Symptoms include browser failures despite "working" network tests. Root causes often involve WinINET proxy misconfiguration, dead localhost listeners, or stack mismatches — not datacenter outage.

Current-state pain:

- IT resets proxy settings without structured evidence
- Security escalates without writer attribution proof
- Risk and audit cannot reconstruct decision rationale
- Repeat incidents lack control-test feedback loops

---

## Current-state process (typical)

```text
User reports browser failure
        ↓
Ad-hoc troubleshooting (ping, DNS, reboot)
        ↓
Manual registry / proxy reset (may work)
        ↓
Ticket closed — no audit trail, no control test
        ↓
Repeat incident — same root cause
```

**Weaknesses:** No proof tier, no preview, no verification, no hash-chained custody.

---

## Target-state process (this platform)

```text
Structured evidence collection (read-only)
        ↓
Classification + limitations[]
        ↓
Control tests (CTRL-001–010)
        ↓
Policy-gated remediation PREVIEW
        ↓
Human confirmation (if apply)
        ↓
Verification + hash-chained audit
        ↓
Governance report / KPI rollup
```

Purple overlay for control validation:

```text
Fixture simulate → Detect → Respond (preview) → Verify → Benchmark
```

---

## Stakeholders

See [stakeholder-map.md](stakeholder-map.md). Primary beneficiaries: IT Operations, Security triage, Technology Risk, Internal Audit, Platform Engineering.

---

## Expected benefits

| Benefit | Mechanism | Status |
|---------|-----------|--------|
| Reduced manual investigation variance | Deterministic classifiers + fixtures | **Implemented** |
| Shorter detection time (MTTD) | `proxy-status`, guardian, startup observability | **Implemented** (local) |
| Better control consistency | CTRL-001–010 mapped tests | **Implemented** |
| Clearer ownership | Stakeholder map + control owners | **Documented** |
| Stronger traceability | Hash-chained audit + governance envelope | **Implemented** |
| Lower unsafe remediation effort | Dry-run default + blocked actions | **Implemented** |
| Reliable management reporting | Governance report, analytics-summary | **Prototype** |
| Control validation metrics | Purple benchmark P/R/F1 | **Prototype** |

**No fabricated financial savings.** Use KPIs in [kpi-framework.md](kpi-framework.md) to measure if deployed.

---

## Investment / scope honesty

| Item | Portfolio scope | Production would require |
|------|-----------------|--------------------------|
| Local CLI diagnostics | Yes | Signed agent, fleet policy |
| Audit hash chain | Yes | WORM / SIEM integration |
| FastAPI backend | Demo | OAuth, RBAC, HA |
| Power BI | Blueprint export | Deployed tenant + RLS |
| Purple live mutation | Lab-only design | Isolated lab + rollback proof |

Gap table: [production-readiness-gap.md](production-readiness-gap.md)

---

## Alternatives considered

| Alternative | Why insufficient alone |
|-------------|------------------------|
| Ad-hoc PowerShell scripts | No evidence tiers, audit, or policy gates |
| EDR / AV products | Different problem domain — not proxy drift analytics |
| GRC ticketing only | Records decisions — does not collect endpoint evidence |
| Manual runbooks | High variance; weak replay |

See [tradeoffs.md](tradeoffs.md) for architecture trade-offs.

---

## Recommendation

Adopt this platform pattern where **endpoint reliability and control evidence** must be:

1. **Structured** (not anecdotal)
2. **Policy-gated** (not silent mutation)
3. **Auditable** (hash-chained custody)
4. **Testable** (CI safety contracts + purple fixtures)

For portfolio purposes: demonstrates ability to translate ambiguous operational risk into a measurable, controllable, testable system.
