# Security abuse scenarios — maps to tests/security/

See [threat-model.md](threat-model.md) for full table.

| Scenario | Mitigation | Test |
|----------|------------|------|
| Malformed evidence injection | 400/422 validation; quarantine status | `test_abuse_cases.py` |
| Fake endpoint identity | endpoint_id required; audit metadata | `test_abuse_cases.py` |
| Duplicate replay | content_hash idempotency | `test_idempotency.py` |
| Audit tampering | verify_chain failure | `test_abuse_cases.py` |
| Prompt injection in AI text | explanation_guardrails | `test_prompt_injection_guardrails.py` |
| Unsafe remediation request | no /v1 remediation routes | `test_policy_bypass_blocked.py` |
| Malware/MITM overclaim | non-claim regression | `test_abuse_cases.py` |
| Secret leakage in logs | token not in responses | `test_no_secret_leakage.py` |
| API privilege escalation | RBAC 403 | `test_rbac.py` |
| Policy bypass | safety contracts | `test_policy_bypass_blocked.py` |

**Not in scope:** EDR, autonomous remediation, formal audit assurance.
