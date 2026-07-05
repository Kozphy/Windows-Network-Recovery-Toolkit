# AI risk analyst guardrails

Advisory-only explanation layer for technology risk evidence.

## May

- Summarize evidence
- Explain classification limitations
- Suggest missing evidence
- Draft committee-friendly wording
- Explain why a policy gate blocked remediation

## Must not

- Claim malware or confirmed MITM
- Authorize registry changes, process kill, firewall reset, or adapter disable
- Issue formal audit opinion
- Override classifier result, human review, or policy gate

## Validator

[`src/platform_core/ai_risk_analyst/explanation_guardrails.py`](../src/platform_core/ai_risk_analyst/explanation_guardrails.py)

```python
validate_explanation_text(text) -> ExplanationValidationResult
# is_safe, violations[], recommended_rewrite
```

`LocalRuleBasedAnalyst` sanitizes narrative fields before return.

## Unsafe phrase examples

- malware confirmed
- MITM confirmed
- safe to disable automatically
- kill the process
- reset the firewall
- audit opinion
- AI approved remediation

## Positioning

AI-assisted — not AI-authorized. Humans approve risky actions with typed confirmation.
