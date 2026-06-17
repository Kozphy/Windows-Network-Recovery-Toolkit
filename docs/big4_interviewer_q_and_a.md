# Big 4 Interviewer Q&A

Anticipated questions for Technology Risk, IT Audit, Cyber Risk, Consulting, and FinTech interviews.

---

## Q1. Is this a cybersecurity tool?

**A.** It is **security-adjacent technology risk infrastructure**, not antivirus, EDR, or XDR. It supports evidence-based triage, control testing, and governance — helping teams decide *what we know*, *what we can prove*, and *what remediation is allowed* — without replacing endpoint protection products.

---

## Q2. Why does this matter to Big 4?

**A.** Big 4 risk advisory work often requires translating technical failure modes into **control weaknesses**, **audit evidence**, **risk ratings**, **remediation plans**, and **management reporting**. This platform demonstrates that translation on a concrete, demoable case — dead WinINET proxy with proof-supported classification and preview-only remediation.

---

## Q3. What controls does this project demonstrate?

**A.**

- **Incident management** — structured evidence, timeline, replay
- **Change management** — policy-gated remediation, typed confirmation, rollback
- **Configuration drift detection** — WinINET/WinHTTP contrast, proxy-watch
- **Evidence quality** — observation vs proof tiers, limitations on every output
- **Remediation governance** — dry-run default, blocked destructive actions
- **Audit trail integrity** — append-only hash-chained JSONL
- **Operational resilience** — deterministic fixtures, CI safety contracts

See [technology_risk_control_matrix.md](technology_risk_control_matrix.md).

---

## Q4. How do you avoid false conclusions?

**A.** The system separates **observation**, **correlation**, **proof**, and **final causation**. Findings require evidence; correlation cannot unlock final causation without strong telemetry. Every report includes `limitations[]`. Confidence is **ordinal (0–1)**, not a statistical probability. Principles are enforced in code and CI: Observation ≠ Proof; Correlation ≠ Causation.

---

## Q5. How would this apply to FinTech?

**A.** FinTech platforms need strong **operational resilience**, **auditability**, **control evidence**, and **safe remediation**. The same model applies to payment outages, API failures, TLS issues, cloud incidents, and suspicious infrastructure changes. Endpoint proxy drift is a **governed microcosm** — the workflow scales to production services with appropriate adapters.

See [fintech_operational_risk_case.md](fintech_operational_risk_case.md).

---

## Q6. What would you improve next?

**A.**

- **RBAC** and production authentication on FastAPI
- **SIEM export** (Splunk, Sentinel) for audit events
- Stronger **Sysmon / Event Log** integration for registry writer proof
- **Policy-as-code** for change windows and approval workflows
- **Cloud incident adapters** (ALB, API Gateway, service mesh)
- Fleet-scale correlation across thousands of endpoints

---

## Q7. How is this different from a PowerShell fix script?

**A.** Scripts optimize for speed of fix. This platform optimizes for **decision quality**: evidence tiers, proof engine, risk rating, control tests, audit trail, and remediation gates. A script can be one step inside an approved remediation; it cannot replace governance artifacts auditors expect.

---

## Q8. Does this prove malware?

**A.** **No.** A dead localhost proxy with supported proof indicates a **reliability** root cause. Malware or unauthorized persistence requires additional telemetry (e.g. registry writer attribution, software inventory, EDR correlation). The platform documents unproven areas explicitly.

---

## Q9. Can it remediate automatically?

**A.** **No by default.** Remediation is preview-only (`dry_run=true`) until policy allows apply, operator supplies typed confirmation (e.g. `DISABLE_WININET_PROXY`), rollback plan is present, and audit logging is enabled. This is intentional — autonomous remediation creates operational and compliance risk.

---

## Q10. How do you test this in CI without Windows?

**A.** Golden fixtures under `tests/fixtures/` drive classification, proof, risk assessment, and control tests on Linux CI. Live WinINET/registry probes run on Windows. Safety contract tests assert blocked actions never execute silently.

---

## Related

- [big4_interview_positioning.md](big4_interview_positioning.md)
- [safety_model.md](safety_model.md)
- [proof-vs-observation.md](proof-vs-observation.md)
