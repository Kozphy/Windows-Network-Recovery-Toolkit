# Consulting Case Study — Technology Risk & Control Analytics Platform

**Client context (representative):** Mid-market enterprise with hybrid workforce, heavy SaaS/SSO dependency, and decentralized L1/L2 support.

---

## Business objective

Restore reliable browser and business-application access while maintaining **audit evidence**, **change governance**, and **honest uncertainty** about security root cause.

---

## Consulting frame

```text
Business Objective → Asset → Threat → Control → Testing → Finding → Risk Rating → Remediation → Governance
```

| Stage | This case |
|-------|-----------|
| **Business Objective** | Maintain reliable and secure browser/network access |
| **Asset** | Windows endpoint WinINET proxy configuration |
| **Threat** | Dead localhost proxy (`127.0.0.1:59081`) breaks browser traffic |
| **Control** | Proxy drift detection; policy-gated remediation; audit trail |
| **Testing** | WinINET/WinHTTP contrast; listener check; proof envelope |
| **Finding** | `DEAD_PROXY_CONFIG` + `WININET_WINHTTP_MISMATCH` (proof-supported) |
| **Risk Rating** | Inherent Medium; residual Medium-Low after controls |
| **Remediation** | Preview WinINET proxy disable — not apply without approval |
| **Governance** | `PREVIEW_ONLY`, dry-run, typed confirmation, rollback, audit JSONL |

---

## STAR narrative

### Situation

Users reported browsers and dev tools failing while ping and DNS continued to work. Initial tickets were misrouted as "network outage." WinINET registry showed proxy enabled toward `127.0.0.1:59081`; WinHTTP remained direct. No process listened on port 59081.

### Task

Design a **repeatable triage workflow** that:

1. Separates observation from proof
2. Produces audit-ready evidence for IT Risk and Internal Audit
3. Gates remediation behind policy — no silent registry changes
4. Documents what **cannot** be proven (malware, MITM, registry writer)

### Action

Built a Python/FastAPI **Technology Risk & Control Analytics Platform**:

- **Evidence collectors** for WinINET, WinHTTP, listener state, TLS contrast
- **Proof engine** (`diagnose --proof`) with explicit limitations
- **Risk classification** (12 primary labels + secondary signals)
- **Business/control layer** mapping incidents to objectives, assets, threats, controls
- **Policy engine** — dry-run default, blocked destructive actions
- **Audit trail** — append-only JSONL with hash chain and replay
- **CI safety contracts** — fixture-based tests on every PR
- **Management reporting** — `governance-report --format markdown`

### Result

- Reduced false escalations to "security incident" for a reliability root cause
- Produced **audit-ready** incident pack with evidence tiers and limitations
- Enabled **control testing** demonstration for ITGC-style reviews
- Remediation remained **preview-only** until typed confirmation and rollback review

**Honest residual risk:** Without Sysmon E13 or equivalent, registry writer remains unproven — documented in every report.

---

## Deliverables a consultant would hand to the client

1. **Control matrix** — [technology_risk_control_matrix.md](technology_risk_control_matrix.md)
2. **Risk assessment JSON** — `risk-assess --fixture case_1_dead_wininet_proxy.json`
3. **Control test results** — `control-test` output with PASS/FAIL per control
4. **Governance report** — markdown management summary
5. **Operational playbook** — [consulting-report.md](consulting-report.md) Phase 1–5
6. **Limitations appendix** — proof does not equal malware verdict

---

## Differentiation from a script

| One-off script | This platform |
|----------------|---------------|
| Registry reset | Policy-gated preview + typed token |
| "Fix it" mentality | Evidence → proof → risk → governance |
| No audit trail | Hash-chained JSONL + replay |
| False certainty | limitations[] on every output |
| Laptop-only | Fixture CI on Linux; Windows live probes |

---

## Related

- [big4_demo_flow.md](big4_demo_flow.md)
- [case-studies/dead-localhost-proxy.md](case-studies/dead-localhost-proxy.md)
- [interview_pitch_5_minutes.md](interview_pitch_5_minutes.md)
