# Big 4 Interview Positioning — Technology Risk & Control Analytics Platform

## One-line pitch

**Built a Technology Risk & Control Analytics Platform that transforms endpoint reliability incidents into evidence-backed risk assessments, control tests, remediation previews, audit trails, and governance reports.**

---

## Business problem

Modern enterprises face endpoint, proxy, TLS, browser, and application-layer failures where **IT support**, **security**, **compliance**, and **audit** teams may disagree about cause and remediation.

Typical symptoms:

- Ping and DNS succeed; browsers and SSO fail
- WinINET proxy points at a dead localhost port
- WinINET and WinHTTP paths diverge
- Unknown local proxy listeners appear without registry writer proof
- TLS certificate paths differ between direct and proxied routes

Traditional fix scripts mutate registry state without evidence tiers, control testing, or audit trails — creating **operational risk**, **compliance exposure**, and **false security conclusions**.

This platform provides **structured evidence**, **risk classification**, **control testing**, and **audit-ready reporting** so technology risk decisions are defensible to management and auditors.

---

## Big 4 relevance

| Practice area | How this project maps |
|---------------|----------------------|
| **IT General Controls (ITGC)** | Configuration monitoring, change governance, audit trail integrity |
| **Change management** | Policy-gated remediation preview; typed confirmation; rollback review |
| **Incident management** | Evidence pipeline, timeline merge, deterministic replay |
| **Access / privilege safety** | Blocks silent kill, firewall reset, adapter disable by default |
| **Audit evidence quality** | Evidence tiers; limitations[] on every report; hash-chained JSONL |
| **Control testing** | `control-test` CLI; PASS/FAIL/WARNING per control objective |
| **Risk rating** | Inherent/residual levels with explicit confidence limitations |
| **Management reporting** | `governance-report --format markdown` |
| **Remediation governance** | Dry-run default; PREVIEW_ONLY unless policy satisfied |
| **Regulatory / FinTech operational resilience** | Same model applies to payment/API outages, TLS issues, suspicious infra changes |

---

## Consulting framing

```text
Business Objective
      ↓
    Asset
      ↓
Threat / Failure Mode
      ↓
Control
      ↓
Control Test
      ↓
Finding (evidence-backed)
      ↓
Risk Rating
      ↓
Remediation Recommendation
      ↓
Governance / Audit Trail
```

**Golden case:** Dead WinINET proxy `127.0.0.1:59081` — browser fails, no listener, proof supported, remediation preview-only.

---

## Interview story (STAR)

| | |
|---|---|
| **Situation** | Browser and dev tools failed while DNS/ping worked. WinINET showed `ProxyEnable=1` and `ProxyServer=127.0.0.1:59081`. WinHTTP was direct. No listener on 59081. |
| **Task** | Build a safer way to diagnose, prove, classify, and remediate **without** blindly changing registry or network settings. |
| **Action** | Built evidence collectors, proof engine, risk classification, policy gates, dry-run remediation, append-only audit trail, replay, FastAPI endpoints, dashboard, Prometheus metrics, and CI safety contracts. Added business/control layer (`risk-assess`, `control-test`, `governance-report`). |
| **Result** | Converted a technical incident into an **audit-ready technology risk workflow** with explicit limitations — not a malware verdict. |

---

## Important disclaimers

- **Not malware detection.** Heuristic scores support triage, not automated blocking.
- **Not autonomous remediation.** Apply requires policy gate, typed confirmation, rollback plan, and audit logging.
- **Not EDR/XDR.** No endpoint agent replacement; complements existing security tooling.
- **Does not claim final causation** unless telemetry is strong enough (e.g. Sysmon E13 registry writer + network impact proof).
- **Confidence is ordinal (0–1), not probability.** Every output includes `limitations[]`.
- **All destructive actions** require policy gate, typed confirmation, rollback plan, and audit trail.

---

## Technical credibility (for depth questions)

- WinINET / WinHTTP contrast, registry writer attribution design (Sysmon E13)
- TLS direct vs proxied certificate proof
- Policy engine with dry-run default and blocked action list
- Append-only hash-chained JSONL audit with deterministic replay
- FastAPI platform API, Prometheus metrics, fixture-based CI on Linux + Windows live probes
- Python 3.11+, Pydantic v2, 1000+ pytest including safety contracts

---

## Related materials

- [technology_risk_control_matrix.md](technology_risk_control_matrix.md)
- [interview_pitch_90_seconds.md](interview_pitch_90_seconds.md)
- [big4_demo_flow.md](big4_demo_flow.md)
- [big4_interviewer_q_and_a.md](big4_interviewer_q_and_a.md)
