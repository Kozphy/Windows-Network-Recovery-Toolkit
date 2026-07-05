# Portfolio positioning and interview guides

Audience-specific framing moved from the root README. Technical depth lives in linked docs — not duplicated here.

## Who this is for

| Audience | Why it matters |
|----------|----------------|
| **Big 4 / technology risk / IT audit** | Control testing, proof tiers, governance reports, CTRL-001–010 |
| **Platform / SRE** | Deterministic classifiers, replay benchmarks, CI safety contracts |
| **FinTech / operational risk** | Policy-gated remediation, audit trail, management reporting |
| **Internal audit / IT governance** | Hash-chained JSONL, replay verification, non-accusatory classifications |
| **Data / BI / PL-300** | Star-schema CSV export, KPI rollups, report blueprint |
| **AI governance** | Advisory-only AI boundaries; humans authorize execution |
| **MSc / research** | Reproducible evaluation harness, limitations register |

## Start here by role

| If you are… | Read first |
|-------------|------------|
| Big 4 / audit | [big4-interview-defense.md](big4-interview-defense.md) · [control-matrix.md](control-matrix.md) · [../reports/sample_governance_report.md](../reports/sample_governance_report.md) |
| Platform / SRE | [faang-platform-review.md](faang-platform-review.md) · [state-machine.md](state-machine.md) |
| Power BI / analytics | [../analytics/powerbi/report_blueprint.md](../analytics/powerbi/report_blueprint.md) · [powerbi-interview-story.md](powerbi-interview-story.md) |
| Research / MSc | [research-framing.md](research-framing.md) · [evaluation.md](evaluation.md) · [msc-application-summary.md](msc-application-summary.md) |
| Timed demo | [interview-demo-3min.md](interview-demo-3min.md) |

---

## By portfolio angle

### Big 4 technology risk / IT audit

- CTRL-001–010 control matrix with pass/fail interpretation
- Proof ladder T0–T5 and governance report sample
- Management information framing — **not** a formal audit opinion
- [big4-interview-defense.md](big4-interview-defense.md)

### Platform / SRE

- Deterministic classifiers and proxy state machine
- Replay benchmarks and fleet simulate
- Observability-shaped metrics and Docker demo stack
- [faang-platform-review.md](faang-platform-review.md)

### FinTech risk and controls

- Policy-gated remediation previews
- Ordinal risk ratings with limitations
- Audit hash chain before committee export

### Data / BI analytics

- `powerbi-export` / `export-powerbi` star-schema and flat CSV
- DAX blueprint and RLS design docs
- [powerbi-interview-story.md](powerbi-interview-story.md) · [../analytics/powerbi/schema.md](../analytics/powerbi/schema.md)

### AI governance / decision intelligence

- Advisory-only AI analyst with guardrails
- Human review queue and proof-tier caps
- [ai-risk-analyst-guardrails.md](ai-risk-analyst-guardrails.md) · [ai-evals-feedback-loop.md](ai-evals-feedback-loop.md)

### Home / SOHO LAN privacy

- CTRL-LAN-001..008, privacy risk score, router evidence import
- [lan-privacy-monitor.md](lan-privacy-monitor.md) · [privacy-risk-score.md](privacy-risk-score.md)

---

## Interview talking points

1. **Why not a PowerShell fix script?** — Audit trail, proof tiers, policy gates, replay.
2. **How do you avoid false malware accusations?** — Classification is not accusation; `limitations[]` on every output.
3. **How do you prevent autonomous damage?** — Dry-run default, typed tokens, CI safety contracts.
4. **Where does AI fit?** — Explanation acceleration only; decisions stay evidence-backed.
5. **Show auditability.** — `audit verify` + governance report from audit directory.
6. **Is this EDR or spyware detection?** — No — reliability and control analytics with explicit non-claims.

---

## Deep references

- [PORTFOLIO.md](../PORTFOLIO.md)
- [SYSTEM_DESIGN.md](../SYSTEM_DESIGN.md)
- [DOCUMENTATION_INDEX.md](DOCUMENTATION_INDEX.md)
- [production-readiness-gap.md](production-readiness-gap.md)
- [threat-model.md](threat-model.md)
- [upgrade-deliverables.md](upgrade-deliverables.md)
