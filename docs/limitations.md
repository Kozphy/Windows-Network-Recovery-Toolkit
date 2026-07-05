# Limitations Register

Version: 1.0 · Applies to all classifications, reports, and CLI output.

---

## Platform Boundaries

| Limitation | Implication |
|------------|-------------|
| **Not EDR/SIEM/ITSM** | Does not replace enterprise security or ticket systems |
| **Not malware attribution** | Labels are reliability triage; never `MALWARE_DETECTED` |
| **Not MITM confirmation** | `POSSIBLE_MITM_RISK` only; never `MITM_CONFIRMED` |
| **Not autonomous repair** | Preview-only default; humans authorize apply |
| **Not endpoint safety guarantee** | Improved observability ≠ secured endpoint |
| **Windows-first** | Live collectors target Windows; CI uses fixtures |
| **Writer attribution gap** | Without Sysmon E13/Procmon, registry writer unproven |
| **Ordinal confidence** | Scores rank severity; not calibrated probabilities |
| **Management information** | Governance reports are not formal audit opinions |

---

## Operational Limitations

- Group Policy proxy settings may override user registry reads
- IPv6 loopback and ephemeral ports may be missed by heuristics
- Browser vs curl TLS paths differ for legitimate reasons (cert store, SNI)
- Demo API auth is not production-hardened
- SQLite/Postgres dual persistence requires explicit correlation in mixed deployments

---

## Required Disclosure

Every `ClassificationResult` and governance report **must** include `limitations[]`. CI enforces via `tests/test_non_claim_regression.py` and `tests/test_proxy_classifier_safety_contract.py`.

---

## Related

- [safety-model.md](safety-model.md)
- [proof-tiers.md](proof-tiers.md)
- README non-claims table
