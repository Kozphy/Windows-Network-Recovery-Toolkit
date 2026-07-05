# MSc / Research Application Summary

Project: **Technology Risk & Control Analytics Platform for Windows Endpoint Reliability**

---

## 150-Word Version

Windows endpoints often fail while appearing online—dead localhost proxies, WinINET/WinHTTP drift, and TLS path mismatches. I built an evidence pipeline that converts these signals into classified incidents, proof tiers (T0–T5), policy-gated remediation previews, hash-chained audit trails, and governance reports. The system enforces safety contracts: no silent registry changes, no autonomous repair, and explicit limitations on every classification. Evaluation uses fifteen controlled scenarios with offline replay benchmarks. The work sits at the intersection of platform engineering, technology risk, and explainable operational decision-making—not antivirus or EDR replacement.

---

## 300-Word Version

Corporate laptops frequently exhibit browser failures while ping and DNS succeed. Root causes include stale WinINET proxy settings pointing at closed localhost ports, divergence between WinINET and WinHTTP stacks, and unknown local listeners that are often misclassified as security incidents.

I designed and implemented a **Technology Risk & Control Analytics Platform** that structures this problem as an auditable evidence chain: Signal → Evidence → Classification → Proof Tier → Policy Gate → Action Preview → Audit Trail → Governance Report. A rule-based classifier assigns twelve primary labels (e.g., `DEAD_PROXY_CONFIG`, `REVERTER_SUSPECTED`) with ordinal confidence and mandatory `limitations[]`.

Proof tiers govern what language and remediation are permitted—observation (T0) through governance-confirmed apply (T5). Policy gates default to preview-only remediation; destructive actions are blocked in CI. The platform exports Power BI star-schema CSVs and supports deterministic fixture replay for training and regression testing.

The project demonstrates research-oriented systems thinking: reproducibility, falsifiable evaluation scenarios, and honest boundary statements. It is portfolio-grade engineering suitable for applied MSc programmes in data science, software engineering, or cyber risk—and for technology risk / platform interviews—without claiming formal audit opinions or malware detection.

---

## 500-Word Version

**Problem.** Endpoint reliability failures on Windows are routinely handled as ad-hoc IT tickets. Operators lack a shared evidence model, conflate correlation with causation, and apply registry fixes without audit trails. Security teams may over-escalate benign dev proxies; reliability teams may under-document control failures.

**Approach.** I implemented a local-first platform that treats endpoint proxy drift as a **technology risk analytics** problem. Read-only collectors gather WinINET, WinHTTP, listener, and optional TLS/browser path evidence. A classification engine maps observations to twelve primary labels with secondary signals. Proof tiers (T0–T5) constrain claim strength and remediation permissions. A policy engine enforces preview-only defaults and blocks process kill, firewall reset, and adapter disable without explicit human confirmation.

**Architecture.** The codebase separates collectors, classifiers, policy, audit (hash-chained JSONL), and reporting modules. A FastAPI backend supports enterprise-shaped ingestion; a CLI provides operator workflows (`diagnose --proof`, `evidence-report`, `audit verify`, `export-powerbi`). Fifteen controlled evaluation scenarios and pytest safety contracts provide regression coverage.

**Governance.** Outputs include committee-ready governance reports explicitly positioned as management information—not SOC 2 opinions. Power BI exports enable incident trending and control testing dashboards. AI assists explanation drafting only; humans authorize execution.

**Limitations.** Windows-first live probes; writer attribution requires optional Sysmon telemetry; confidence is ordinal not probabilistic; the tool does not replace EDR, SIEM, or ITSM.

**Fit.** This work demonstrates applied research skills: problem framing, methodology, evaluation design, and safety-conscious engineering—relevant to Manchester/Russell Group MSc programmes in advanced computer science, cyber security, or data science, and to Big 4 technology risk / platform SRE roles.

---

## Manchester / Russell Group Applied MSc

Emphasize: **reproducible evaluation**, **open fixture corpus**, **Python/FastAPI implementation**, **governance analytics**, **ethical AI boundaries** (advisory-only). Link to [research-framing.md](research-framing.md) and [evaluation.md](evaluation.md).

---

## Cambridge / Oxford Research-Oriented Framing

Emphasize: **research question** on evidence-based endpoint governance, **methodological contribution** (proof tiers + policy gates), **limitations register**, **future work** (calibrated confidence, fleet-scale validation). Avoid overselling production readiness; foreground falsifiability and threat-to-validity discussion in [limitations.md](limitations.md).

---

## SOP Paragraph (paste-ready)

My independent project addresses how Windows endpoint reliability failures can be governed through reproducible evidence tiers rather than ad-hoc repair scripts. I built a platform that classifies proxy-drift incidents, gates remediation behind preview-only policy defaults, and produces hash-chained audit trails and governance reports with explicit limitations. The work reflects my interest in explainable systems, technology risk, and safe automation—combining software engineering with audit-aware design.

---

## Interview Links

- Big 4: [big4-interview-defense.md](big4-interview-defense.md)
- Platform/SRE: [faang-platform-review.md](faang-platform-review.md)
- 3-min demo: [interview-demo-3min.md](interview-demo-3min.md)
