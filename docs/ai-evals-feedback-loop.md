# AI Evals Feedback Loop

Optional module demonstrating how the platform’s evidence, classification, policy-gate, and governance-reporting architecture applies to **GenAI / LLM evaluation** — without replacing the endpoint reliability platform.

## Why this module exists

Forward Deployed Engineering and AI evals work often needs the same discipline as technology risk:

- Separate **observation from proof**
- Classify failures with **limitations**, not certainty
- Gate recommendations behind **human review**
- Produce **auditable reports** for partner feedback loops

This module is a **portfolio-grade evaluation harness** — not a formal model safety certification, production deployment gate, or audit opinion.

## Pipeline mapping

| Endpoint reliability platform | AI evals feedback loop |
|------------------------------|------------------------|
| Observation (signals) | Prompt / task input |
| Hypothesis | Expected facts / answer |
| Proof | Citation & fact checks |
| Classification | Failure taxonomy labels |
| Policy decision | Eval policy gate |
| Audit log | Eval run metadata (fixture-only) |
| Governance report | AI Evals Feedback Loop Report |

```text
Prompt / Task Input → Model Output (fixture) → Expected Evidence
  → Evaluation Result → Failure Classification → Policy Decision
  → Audit metadata → Model Quality Report
```

## Architecture

| File | Role |
|------|------|
| [`src/platform_core/ai_evals/schemas.py`](../src/platform_core/ai_evals/schemas.py) | Pydantic models: `EvalCase`, `EvalResult`, `EvalReport` |
| [`src/platform_core/ai_evals/failure_taxonomy.py`](../src/platform_core/ai_evals/failure_taxonomy.py) | `FailureLabel`, `EvalPolicyGate`, baseline limitations |
| [`src/platform_core/ai_evals/evaluator.py`](../src/platform_core/ai_evals/evaluator.py) | Deterministic checks (no external API) |
| [`src/platform_core/ai_evals/policy.py`](../src/platform_core/ai_evals/policy.py) | Failure label → policy gate |
| [`src/platform_core/ai_evals/report.py`](../src/platform_core/ai_evals/report.py) | Markdown / JSON report renderer |

## Failure taxonomy

| Label | Meaning |
|-------|---------|
| `CORRECT` | Output aligns with expected facts and format |
| `HALLUCINATION_RISK` | Elevated risk — claim not grounded in context |
| `RETRIEVAL_MISS` | Required fact missing from output |
| `UNSUPPORTED_CLAIM` | Statement lacks support in context/facts |
| `FORMAT_VIOLATION` | Required format (e.g. JSON) not satisfied |
| `REFUSAL_UNEXPECTED` | Refusal or empty output when answer expected |
| `SAFETY_REVIEW_REQUIRED` | Risky phrasing — human review before use |
| `INSUFFICIENT_EVIDENCE` | Required citations missing |
| `LATENCY_OR_COST_REGRESSION` | Latency/cost exceeds fixture threshold |

Language is **risk / limitation** based — we do not claim the model is “lying” or “unsafe” with certainty.

## Policy gates

| Gate | Typical trigger |
|------|-----------------|
| `ALLOW` | `CORRECT` with sufficient evidence markers |
| `PREVIEW` | Format or cost/latency issues |
| `REQUIRE_HUMAN_REVIEW` | Retrieval miss, refusal, unsupported claim (medium severity) |
| `BLOCK` | Safety phrasing, high-severity hallucination risk |
| `INSUFFICIENT_EVIDENCE` | Missing required citations |

**Principle:** Recommendation is not execution authority. `ALLOW` does not authorize production deployment.

## Demo command

```powershell
python -m windows_network_toolkit ai-eval `
  --cases examples/ai_evals/support_bot_cases.json `
  --format markdown
```

JSON output:

```powershell
python -m windows_network_toolkit ai-eval --format json
```

Fixture dataset: [`examples/ai_evals/support_bot_cases.json`](../examples/ai_evals/support_bot_cases.json)

## Example report sections

The markdown report includes:

1. Executive summary (pass / fail / partial counts)
2. Eval dataset overview
3. Metrics summary table
4. Failure taxonomy distribution
5. Policy decisions
6. High-risk cases requiring human review
7. Limitations and non-claims
8. Recommended next actions

Footer: *This report is not a formal model safety certification.*

## Safety boundaries

This module does **not**:

- Call live LLM APIs (all outputs are fixture data)
- Certify model safety or production readiness
- Replace endpoint risk classification or proxy remediation
- Issue malware / MITM verdicts

Epistemic principles (same as endpoint platform):

1. Observation is not proof  
2. Correlation is not causation  
3. Confidence is not certainty (ordinal only)  
4. Classification is not accusation  
5. Policy permission is not a safety guarantee  
6. Recommendation is not execution authority  

## Relation to AI risk analyst

[`docs/ai-risk-analyst-guardrails.md`](ai-risk-analyst-guardrails.md) covers **explanation drafting** for endpoint incidents. This module covers **offline eval harness** for support-bot / RAG scenarios. They are adjacent — not merged.

## Forward Deployed Engineering framing

Partner-facing AI work benefits from **structured eval signals** that teams can iterate on:

- Reproducible fixture suites
- Deterministic failure labels
- Policy-gated recommendations
- Governance-style reports for review meetings

This supports feedback loops without autonomous model deployment or silent policy overrides.

## Tests

```powershell
pytest -q tests/ai_evals/
```
