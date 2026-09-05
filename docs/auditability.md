# Auditability

**Platform:** Technology Risk & Control Analytics for Windows endpoints
**Implementation:** [audit-custody.md](audit-custody.md) · [decision-model.md](decision-model.md)

---

## Audit question framework

Internal audit and risk reviewers should be able to answer:

| Question | Supported? | How |
|----------|------------|-----|
| **Who** acted? | Yes | `actor` field in custody records (e.g. `operator_cli`, `guardian`) |
| **What** action? | Yes | `action_type` / event name in JSONL |
| **Which resource?** | Yes | `resource` (e.g. `wininet_proxy`) |
| **When?** | Yes | `timestamp_utc` |
| **Why** (decision basis)? | Partial | Linked evidence in diagnose output; governance envelope |
| **Which evidence?** | Yes | Evidence bundle refs; classification + limitations |
| **What result?** | Yes | `decision`, `result`, verification outcome |

**Not stored:** confirmation token strings, secrets, credentials.

---

## Custody stores

| Store | Role | Integrity |
|-------|------|-----------|
| `.audit/canonical_custody.jsonl` | Hash-chained primary custody | `previous_hash` / `current_hash` |
| `.audit/canonical_custody.tip.json` | Tip anchor for rewrite detection | Tip hash vs last record |
| `logs/*.jsonl` | Legacy operator logs (dual-write) | Not hash-chained alone |
| `platform_data/*.jsonl` | Platform API events | Separate from canonical chain |

Verify:

```powershell
python -m windows_network_toolkit audit verify .audit/canonical_custody.jsonl --check-tip
```

---

## Record shape (conceptual)

```json
{
  "schema_version": "audit_record.v1",
  "timestamp_utc": "2026-08-31T12:00:00Z",
  "actor": "operator_cli",
  "action_type": "PROXY_REMEDIATION_PREVIEW",
  "resource": "wininet_proxy",
  "decision": "PREVIEW_ONLY",
  "confirmation_supplied": false,
  "correlation_id": "uuid-or-preview-id",
  "previous_hash": "...",
  "current_hash": "...",
  "signature_status": "hash_chained"
}
```

Modules: `src/platform_core/audit/writer.py`, `custody.py`, `tip_anchor.py`

---

## Governance envelope (claim vs execution)

JSON outputs may include:

```json
{
  "governance": {
    "claim_strength": "proof",
    "execution_authority": "preview_only",
    "limitations": ["Does not prove malware or MITM."],
    "causal_language_allowed": false
  }
}
```

Module: `src/platform_core/governance/evidence_to_action.py`

Separates **what we can claim** from **what we may execute**.

---

## What we do not claim

| Claim | Reality |
|-------|---------|
| Immutable audit | Local hash chain — not WORM |
| Cryptographic signing | Hash chaining only in v1 |
| SIEM integration | Export manual / API read |
| Formal audit opinion | Management information |

---

## Audit-related controls

| Control | Test |
|---------|------|
| CTRL-010 Audit hash chain | `audit verify`, `tests/test_audit_contract.py` |
| CTRL-009 No silent mutation | `tests/test_policy_safety_contract.py` |
| Token non-storage | Custody mapping tests |

---

## Auditor walkthrough (15 minutes)

1. Run fixture diagnose — capture classification + limitations
2. Run control-test on same fixture
3. Run proxy-disable dry-run — capture PREVIEW_ONLY policy
4. Inspect `.audit/canonical_custody.jsonl` (or fixture audit sample)
5. Run `audit verify --check-tip`
6. Generate governance-report from audit sample dir

UAT: [uat-plan.md](uat-plan.md) UAT-006, UAT-007
