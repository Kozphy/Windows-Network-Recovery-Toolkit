# AI-Assisted Software Delivery

This document explains how AI tools supported development of this platform — and what was **not** delegated to AI.

---

## How AI was used during development

| Area | AI assistance | Human review |
|------|---------------|--------------|
| Documentation structure | Draft README sections, portfolio narratives | Accuracy, positioning, no EDR/antivirus claims |
| Test scaffolding | Suggested pytest cases for safety contracts | All assertions verified against real code paths |
| Report templates | Markdown incident report outlines | Evidence language, disclaimers, governance principles |
| Code exploration | Navigation, refactor suggestions | Every merge reviewed; CI must pass |
| Demo scripts | 3-minute walkthrough drafts | Commands validated on fixtures |

AI accelerated **explanation, documentation, and test ideas** — not autonomous risk verdicts or remediation.

---

## What was reviewed manually

- **Safety boundaries** — dry-run defaults, typed confirmation tokens, forbidden destructive verbs  
- **Epistemic principles** — six governance rules in `evidence_to_action.v1`  
- **Classification labels** — triage wording; no malware accusations  
- **Policy outcomes** — PREVIEW_ONLY vs execution paths  
- **Public positioning** — explicit “not EDR/antivirus/XDR” disclaimers  
- **CI contracts** — `test_policy_safety_contract.py` and replay determinism  

---

## Hallucination risk controls

1. **Fixture-first development** — golden JSON under `tests/fixtures/` and `examples/evidence/`  
2. **Deterministic replay** — same fixture → same classification and policy in CI  
3. **Rule-based fallback** — `LocalRuleBasedAnalyst` when no LLM API key configured  
4. **Guardrails module** — downgrades recommendations when evidence incomplete  
5. **Limitations[] on every outward model** — mandatory uncertainty surfacing  
6. **No AI execution path** — AI cannot call registry, kill, or firewall APIs  

---

## Why AI output is not treated as proof

| Principle | Application |
|-----------|-------------|
| Observation is not proof | AI summarizes observations; proof engine validates |
| Correlation is not causation | AI cannot upgrade listener match to writer proof |
| Confidence is not certainty | Ordinal scores only; AI text cannot imply probability |
| Classification is not accusation | AI must not label compromise without proof tier |
| Recommendation is not execution authority | Policy engine + human confirmation required |

AI narratives are **decision support** — appended to audit with `provider` metadata, never sole evidence.

---

## AI usage transparency (reports and docs)

Generated governance reports include an explicit section stating:

- AI may assist with **explanation, summarization, and report drafting**
- AI does **not** authorize registry changes, process termination, firewall reset, adapter disable, malware verdicts, MITM claims, or control effectiveness attestation
- **Final decisions** require evidence, policy gates, and human review

See `src/platform_core/governance/report_sections.py` and `ai_usage_transparency` in `governance-report` JSON output.

---

## How tests and audit logs validate outputs

```powershell
# Safety contracts
pytest -q tests/test_policy_safety_contract.py tests/test_portfolio_evidence_suite.py

# Portfolio fixtures
pytest -q tests/test_portfolio_case_studies.py

# AI analyst guardrails (no destructive recommendations)
pytest -q tests/test_ai_risk_analyst.py

# Audit chain integrity
python -m windows_network_toolkit audit verify tests/fixtures/analytics/audit_sample/incidents.jsonl
```

Audit rows include: timestamp, action type, evidence refs, policy outcome, and (when used) AI provider + `audit_id` for reasoning metadata.

---

## What AI does not decide

- Whether to disable proxy (human + typed token)  
- Whether a process is malicious  
- Whether MITM is confirmed  
- Whether to kill a process or reset firewall  
- Regulatory or audit sign-off  
- Control effectiveness attestation  

Final risk decisions remain **evidence-backed, policy-gated, and human-reviewable**.
