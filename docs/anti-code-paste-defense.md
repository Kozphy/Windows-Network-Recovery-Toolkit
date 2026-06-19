# Anti–Code-Paste Defense Guide

**Audience:** Portfolio reviewers, Big 4 interviewers, FAANG platform engineering hiring managers, internal audit  
**Purpose:** Demonstrate **ownership** of design decisions — not repository familiarity alone  
**Rule:** If you cannot answer the reviewer questions below without opening the repo, you do not yet own the narrative.

---

## What this document is

This is an **interview and audit defense pack** for the Windows Network Recovery Toolkit / Technology Risk platform. It explains:

- Why the architecture exists (not just what files exist)
- Where honesty boundaries are enforced in code
- How to respond when reviewers suspect AI-generated or copied implementation

---

## Ownership signals (what reviewers look for)

| Signal | Evidence in this project |
|--------|--------------------------|
| **Epistemic discipline** | T0–T5 tiers, `STANDARD_LIMITATIONS`, `unsafe_inferences_blocked` |
| **Safety by default** | `--dry-run`, `SAFE_REMEDIATION_POLICY`, no auto kill |
| **Full-state reasoning** | `proxy_state_machine.classify_transition` — not single-field diffs |
| **Audit honesty** | Hash chain verify, governance non-claims, `confidence_semantics: ordinal_not_probability` |
| **Test-backed claims** | Fixture matrix in CI; parametrized classification tests |
| **Explicit non-goals** | Not EDR, not AV, not autonomous remediation |

---

## Architecture you must explain in your own words

```text
Observation (CLI JSON)
  → Normalization (EvidenceEvent + tier + limitations)
  → Classification (full before/after state)
  → Control tests (PASS/FAIL/PARTIAL/NOT_TESTED)
  → Policy gate (preview / human review)
  → Audit append (hash chain)
  → Export (governance-report, powerbi-export)
```

**Key modules to cite by responsibility, not line count:**

- `evidence_schema.py` — normalization, tiers, deterministic ids
- `proxy_state_machine.py` — transitions, reverter correlation, blocked inferences
- `control_tests.py` — six endpoint controls, incident refinement
- `audit_report.py` — governance aggregation, human-review queue
- `powerbi_star_export.py` — star schema with disclaimer-friendly columns

---

## Common reviewer traps

| Trap | Correct response |
|------|------------------|
| "This is antivirus" | Security-adjacent **technology risk** infrastructure — triage and governance, not threat blocking |
| "95% confidence = 95% chance of malware" | **Ordinal** ranking (`ordinal_not_probability`) — not calibrated probability |
| "Listener proves who changed registry" | **Correlation only** until Sysmon E13 / Procmon writer proof (T4) |
| "Hash chain proves findings true" | Chain proves **append integrity** — not observation truth |
| "FAIL means kill the process" | FAIL triggers **human review** — recommendations cite telemetry collection |
| "Power BI shows security incidents" | Shows **classified reliability/triage** labels with `is_security_accusation=false` |

---

## Demonstrable commands (run live in review)

```powershell
# 1. Dead proxy — classification + proof
python -m windows_network_toolkit diagnose --proof --fixture tests/fixtures/enert/dead_proxy_59081.json

# 2. Control tests on case study
python -m windows_network_toolkit control-test --fixture tests/fixtures/case_studies/case_1_dead_wininet_proxy.json

# 3. Safe remediation default
python -m windows_network_toolkit proxy-disable --dry-run

# 4. Governance report with control summary
python -m windows_network_toolkit governance-report --audit-dir tests/fixtures/risk_analytics/audit_sample --format markdown

# 5. Audit chain verify
python -m windows_network_toolkit audit verify logs/canonical_decision_audit.jsonl

# 6. Power BI export
python -m windows_network_toolkit powerbi-export --audit-dir tests/fixtures/risk_analytics/audit_sample --out-dir examples/powerbi/export
```

---

## Reviewer questions I should be able to answer

### 1. Is this a cybersecurity product like EDR or antivirus?

**No.** It is endpoint **reliability and technology risk** infrastructure. It reads proxy configuration, compares paths, classifies triage labels, and gates remediation — it does not block threats, collect kernel telemetry at EDR depth, or replace AV signatures.

### 2. Does this prove malware or compromise?

**No.** Classifications like `UNKNOWN_LOCAL_PROXY` are investigative triage. Malware verdicts require EDR, forensics, and writer attribution beyond default toolkit scope. Outputs explicitly block malware accusation without proof.

### 3. Can it remediate automatically?

**No by default.** Remediation is preview-only (`dry_run=true`) until typed confirmation, rollback plan, and audit logging. `SAFE_REMEDIATION_POLICY` documents this; autonomous apply is a non-goal.

### 4. What is the difference between observation and proof?

**Observation** is a read-only fact (registry value, netstat row). **Proof** is a structured check with pass/fail meaning (path probe, writer telemetry). Tiers T0–T5 label claim strength; tiers do not auto-upgrade.

### 5. Why classify proxy transitions from full before/after state?

Single-field diffs cause false labels — e.g. empty `ProxyServer` after removal must not classify as "remote proxy configured." `FORBIDDEN_CLASSIFICATIONS_WHEN_AFTER_SERVER_EMPTY` enforces this safety rule.

### 6. What does listener/process attribution actually prove?

It proves a process was **listening on the configured port** — correlation only. Registry writer identity requires Sysmon Event ID 13 or equivalent (T4). Process name is not writer proof.

### 7. How do you detect a proxy reverter?

`detect_reverter_loop_pattern` looks for repeated enable/disable cycles on the same localhost port within a time window — **correlation only**. Recommend Sysmon registry traces before process action.

### 8. What does PASS on a control test mean?

The control **objective was met for the scoped evidence** — not that the endpoint is secure, compliant, or malware-free. Always read `limitations[]`.

### 9. What does the hash chain verify?

`verify_chain` recomputes SHA-256 links from genesis. It detects tampering or breaks in append order. It does **not** verify observation accuracy or completeness.

### 10. Why is confidence ordinal, not probability?

Calibrated compromise probability requires labeled datasets and base rates we do not have. Ordinal scores rank triage urgency and align with `risk_scoring_engine` governance limitations.

### 11. How is AI used in this platform?

AI may assist narrative formatting and investigation hints (`AI_TRANSPARENCY_SECTION` in governance report). AI does **not** authorize execution, change policy gates, or upgrade proof tiers.

### 12. How do you test without Windows in CI?

Golden fixtures under `tests/fixtures/` drive classification, control tests, and proof envelopes on Linux. Live registry/netstat probes run on Windows agents separately.

### 13. What does the governance report NOT prove?

It does not provide a formal audit opinion, SOX attestation, population-wide operating effectiveness, or malware prevalence. It aggregates audit JSONL with explicit non-claims.

### 14. How does Power BI avoid misleading security dashboards?

`dim_classification.is_security_accusation` defaults false; measures document zero expected accusation count; `has_limitations` flags rows needing tooltip caveats. Seed data may be included for portfolio — label as demo scope.

### 15. What would you build next for production fleet scale?

RBAC on API, Sysmon/E13 integration for writer proof, SIEM export, fleet aggregation, signed packages, and policy-as-code change windows — explicitly documented as roadmap, not current claims.

---

## Red flags that suggest code-paste (avoid these in interviews)

- Claiming MITM or malware without citing tier and limitations
- Describing confidence as "percentage chance of attack"
- Saying hash chain "proves the investigation is correct"
- Unable to name a single control FAIL recommendation that is preview-only
- Presenting Power BI charts without governance disclaimer
- Conflating `CTRL-EPR-001` mature tests with SOX test results

---

## Green flags that demonstrate ownership

- Walk through dead proxy case: observation → T3 probe → `DEAD_PROXY_CONFIG` → CTRL-001 FAIL → preview disable
- Explain why `PARTIAL` on owner verification is expected without Sysmon
- Show `unsafe_inferences_blocked` in transition classification output
- Run `audit verify` and explain genesis-linked hashes
- Cite ADR decisions (evidence-to-action, not EDR, ordinal confidence)

---

## Related documents

- [demo-faang-big4-review.md](demo-faang-big4-review.md) — timed demo paths
- [big4_interviewer_q_and_a.md](big4_interviewer_q_and_a.md) — extended Q&A
- [adr/](adr/) — Architecture decision records
- [evidence_to_action_governance_model.md](evidence_to_action_governance_model.md) — six principles
