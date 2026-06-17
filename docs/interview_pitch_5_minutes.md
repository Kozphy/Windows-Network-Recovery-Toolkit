# 5-Minute Interview Pitch — Technology Risk & Control Analytics Platform

---

## 1. Problem (45 seconds)

Enterprise endpoints fail in ways that look like network outages but are often **configuration drift** — especially WinINET proxy settings pointing at dead localhost ports.

The operational risk is not only downtime. It is:

- **Unaudited changes** to registry and network settings
- **False security conclusions** (listener ≠ registry writer)
- **Remediation that destroys evidence** or causes secondary outages
- **Audit teams unable to reconstruct** what happened

Traditional scripts fix symptoms. Risk and audit teams need **evidence quality**, **control testing**, and **governance reporting**.

---

## 2. Architecture (60 seconds)

```text
Evidence Collectors (WinINET, WinHTTP, listeners, TLS)
        ↓
Classification + Proof Engine (diagnose --proof)
        ↓
Technology Risk Layer (objectives, assets, threats, controls)
        ↓
Control Tests + Findings + Risk Rating
        ↓
Policy Engine (dry-run default)
        ↓
Remediation Preview → Audit JSONL → Replay → API / Dashboard
```

**Canonical core:** `src/platform_core/`  
**CLI:** `python -m windows_network_toolkit` (JSON-first, fixture-safe CI)  
**Principles:** Observation ≠ Proof · Correlation ≠ Causation · Confidence ≠ Certainty

---

## 3. Risk / control mapping (60 seconds)

Walk the consulting frame:

| Step | Golden case (59081) |
|------|---------------------|
| Business objective | Reliable browser access |
| Asset | WinINET proxy configuration |
| Threat | Dead localhost proxy |
| Control | Drift detection + policy-gated remediation |
| Test | WinINET/WinHTTP contrast; listener check |
| Finding | `DEAD_PROXY_CONFIG` + mismatch signal |
| Risk | Medium inherent; residual after controls |
| Remediation | Preview-only WinINET disable |
| Governance | Audit trail, limitations, management report |

Full matrix: [technology_risk_control_matrix.md](technology_risk_control_matrix.md)

---

## 4. Demo flow (90 seconds)

```powershell
$env:PYTHONPATH = (Get-Location).Path

# Step 1 — Observation
python -m windows_network_toolkit proxy-status --fixture tests/fixtures/enert/dead_proxy_59081.json

# Step 2 — Proof
python -m windows_network_toolkit diagnose --proof --fixture tests/fixtures/enert/dead_proxy_59081.json

# Step 3 — Risk assessment
python -m windows_network_toolkit risk-assess --fixture tests/fixtures/case_studies/case_1_dead_wininet_proxy.json

# Step 4 — Control test
python -m windows_network_toolkit control-test --fixture tests/fixtures/case_studies/case_1_dead_wininet_proxy.json

# Step 5 — Management report
python -m windows_network_toolkit governance-report --fixture tests/fixtures/case_studies/case_1_dead_wininet_proxy.json --format markdown

# Step 6 — Safe remediation
python -m windows_network_toolkit proxy-disable --dry-run
```

**Narration tips:**

- After `proxy-status`: "This is **observation** — what we read from the endpoint."
- After `diagnose --proof`: "This upgrades to a **proof envelope** with explicit limitations."
- After `risk-assess`: "Now we're in **management language** — risk rating and governance decision."
- After `proxy-disable --dry-run`: "No destructive action by default."

Full script: [big4_demo_flow.md](big4_demo_flow.md)

---

## 5. Lessons learned (45 seconds)

1. **Epistemic discipline sells trust** — auditors respect `limitations[]` more than overconfident verdicts.
2. **Dry-run default prevents incidents caused by fixes** — especially in FinTech and regulated environments.
3. **Fixture-based CI** makes the platform demoable anywhere (recruiter laptop, CI, interview screen share).
4. **Separate listener attribution from registry writer proof** — critical for honest security language.
5. **Business layer above telemetry** — engineers build collectors; consultants need objectives, controls, and risk ratings.

---

## 6. How this applies to client work (30 seconds)

On a client engagement, the same pattern applies to:

- **ITGC testing** — run control tests, document evidence, rate residual risk
- **Incident response** — structured timeline, replay, management report
- **Technology transformation** — replace tribal scripts with policy-gated decision infrastructure
- **FinTech operational resilience** — API/TLS/cloud incidents with the same governance gates

**Not claiming:** malware detection, EDR replacement, or autonomous remediation.

---

## Supporting materials

- [consulting_case_study.md](consulting_case_study.md)
- [big4_interviewer_q_and_a.md](big4_interviewer_q_and_a.md)
- [resume_bullets_big4.md](resume_bullets_big4.md)
