# Responsible AI Engineering Profile

AI is an explanation and analyst-assistance layer. It does not authorize or execute remediation.

## Architecture contract

1. Deterministic evidence collection and control tests run first.
2. The AI layer receives only approved, minimized evidence.
3. Output uses a structured schema with claims, citations, limitations, confidence band, and recommended reviewer.
4. Policy decisions are made by deterministic code.
5. High-impact and low-confidence outputs enter human review.
6. Every AI invocation records model, prompt version, input evidence IDs, latency, cost metadata, and output hash.

## Evaluation gates

- Citation coverage.
- Unsupported-claim rate.
- Correct abstention when evidence is insufficient.
- Safety-boundary compliance.
- Stable structured-output parsing.
- Regression against versioned golden cases.
- Reviewer agreement and overturn rate.
- Latency and cost budgets.

A release fails when the model recommends unauthorized execution, invents a malware verdict, omits required limitations, or produces uncited high-impact claims.

## Model fallback

- Primary structured model.
- Secondary model or deterministic template.
- Final fallback: no AI explanation; return evidence and limitations only.

AI unavailability must never block deterministic classification, control testing, audit logging, or safe remediation preview.

## Data protection

- Do not send secrets, credentials, personal data, or unrestricted endpoint dumps to external models.
- Apply field-level allowlists and redaction.
- Document model-provider retention and regional-processing assumptions.
- Use synthetic or approved fixtures for evaluation.

## Interview positioning

This profile demonstrates applied AI engineering, LLM evaluation, model-risk controls, observability, human oversight, and graceful degradation rather than a generic chat interface.
