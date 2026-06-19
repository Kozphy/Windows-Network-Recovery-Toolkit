# Big 4 Interview Defense — Technology Risk & IT Audit

Answers for reviewers who ask **“Is this security software?”** or **“Can this replace audit?”**

---

## Why this is not antivirus

- No signature engine, no quarantine, no threat hunting  
- Classifications are **reliability triage** (`DEAD_PROXY_CONFIG`, not `MALWARE_DETECTED`)  
- `unsafe_inferences_blocked[]` explicitly blocks malware accusations without writer proof  
- Scope disclaimer on every governance report  

---

## Why this is not autonomous remediation

- `proxy-disable` defaults to **dry-run**  
- Live apply requires typed token `DISABLE_WININET_PROXY`  
- Process kill, firewall reset, adapter disable are **blocked** in policy registry  
- AI assists explanation — **does not authorize** execution (`docs/adr/0006-ai-assisted-not-ai-authorized.md`)  

---

## How proof tiers avoid overclaiming

| Tier | What you may say |
|------|------------------|
| T0–T1 | Observed configuration |
| T2 | Path/listener probe result |
| T3–T4 | Repeated pattern / timeline |
| T5 | Registry writer correlation (still not malicious intent) |

No tier alone supports a **malware verdict**. See [proxy-proof-ladder.md](proxy-proof-ladder.md).

---

## How control tests map to risk decisions

1. **Detective controls** (CTRL-001–008) produce PASS/FAIL/PARTIAL from fixtures  
2. **Preventive controls** (CTRL-009) verify policy gates in CI  
3. **ITGC-style** (CTRL-010) verify hash chain integrity  
4. Failed health control → elevated **residual risk** in `risk-assess` — not automatic remediation  

Matrix: [control-matrix.md](control-matrix.md)

---

## How Power BI supports risk committee reporting

- Star schema: `fact_incidents`, `fact_control_tests`, `dim_classification`, `dim_proof_tier`  
- KPIs: control pass rate, high-risk count, preview-only remediation ratio  
- **Honest limit:** portfolio semantic export — not deployed Power BI tenant  

See [powerbi-interview-story.md](powerbi-interview-story.md).

---

## Reviewer questions — quick answers

| Question | Answer |
|----------|--------|
| Is this a formal audit opinion? | **No** — management information with limitations |
| Does listener prove registry writer? | **No** — correlation only; Sysmon E13 for writer proof |
| Can AI disable proxy? | **No** — policy + human confirmation only |
| SOC 2 attestation? | **No** — design-effectiveness demo only |

---

## Demo

[interview-demo-3min.md](interview-demo-3min.md) Path B · [one-page-case-study-dead-proxy.md](one-page-case-study-dead-proxy.md)
