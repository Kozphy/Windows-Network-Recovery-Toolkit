# Audit Hash Chain Explained

**Status:** Technical reference for ITGC and internal audit walkthroughs  
**Implementation:** `src/platform_core/governance/chain_of_custody.py`, `src/platform_core/audit/writer.py`  
**Related CLI:** `python -m windows_network_toolkit audit verify <path.jsonl>`

---

## Purpose

The hash chain provides **tamper-evident append-only integrity** for decision audit JSONL. It answers: *Was this log altered after records were written?* — not *Are the observations true?*

---

## Record structure

Each audit record includes:

| Field | Role |
|-------|------|
| Body fields | Command, timestamp, classification, policy outcome, snapshots, limitations |
| `previous_hash` | Prior record's `current_hash`, or `genesis` for first record |
| `current_hash` | SHA-256 of `previous_hash \| canonical_json(body)` |
| `signature_status` | `hash_chained` (metadata — excluded from hash body) |

### Excluded from hash body

`HASH_CHAIN_EXCLUDED_FIELDS`: `previous_hash`, `current_hash`, `signature_status`

This ensures the hash covers decision content, not chain metadata.

---

## Algorithm

```python
# Conceptual — see chain_of_custody.py
body = {k: v for k, v in record.items() if k not in EXCLUDED}
current_hash = SHA256(previous_hash + "|" + json.dumps(body, sort_keys=True))
```

Verification walks records in order:

1. Start `prev = "genesis"`
2. For each record, recompute expected hash from body + prev
3. Compare to stored `current_hash`
4. If mismatch → `(False, "chain break at index N")`
5. Else set `prev = current_hash` and continue

---

## Verify command

```powershell
python -m windows_network_toolkit audit verify logs/canonical_decision_audit.jsonl
python -m windows_network_toolkit audit verify platform_data/audit.jsonl
```

**Pass output:** `verified: true`, message `ok`  
**Fail output:** `verified: false`, index of first break

Governance report surfaces this as `audit_chain_verification.verified` and KPI `hash_chain_invalid_count`.

---

## What verify PROVES

| Claim | Supported? |
|-------|------------|
| Records were appended in order without modifying prior bodies | **Yes** (if verify passes) |
| No record was deleted from middle of chain | **Yes** (subsequent hashes would break) |
| Body content at export time matches hash | **Yes** |
| Decision trail is reproducible for audit period | **Yes**, given complete file |

---

## What verify does NOT PROVE

| Claim | Supported? |
|-------|------------|
| Observations are factually correct | **No** |
| Registry reads were complete | **No** |
| All operator actions were logged | **No** — off-tool actions invisible |
| Writer identity or malware status | **No** |
| Clock timestamps are trustworthy | **No** — NTP drift not validated |
| Backup copies match primary | **No** — verify each file independently |
| Legal non-repudiation of human operator | **No** — no cryptographic signature of person |

---

## Integration points

| Consumer | Usage |
|----------|-------|
| `governance-report` | Blocks attestation narrative when chain invalid |
| `powerbi_star_export` | Calls `verify_chain` when loading audit dir |
| `build_risk_kpi_summary` | Populates `audit_integrity` KPIs |
| CTRL-010 | Control test for evidence integrity |

---

## Failure scenarios

| Scenario | verify result | Response |
|----------|---------------|----------|
| Manual edit of historical row | FAIL at edited index | Do not rely on report; restore backup |
| Truncated file mid-record | FAIL or parse error | Treat as incomplete evidence |
| Empty file | PASS (vacuous) or no-op | NOT_TESTED for CTRL-010 |
| Reordered lines | FAIL | Chain order is semantic |
| Valid chain, false observation | PASS | **Integrity ≠ truth** — investigate observation source |

---

## Audit walkthrough script (60 seconds)

1. "We append decisions to JSONL with genesis-linked SHA-256."
2. "Verify recomputes every hash — any tamper breaks the chain at an index."
3. "This satisfies **integrity** ITGC questions — not **accuracy**."
4. "Governance report runs verify before KPI export."
5. "Limitation: actions outside the toolkit are out of scope."

---

## Comparison to digital signatures

| Mechanism | Provides |
|-----------|----------|
| Hash chain | Ordered integrity, tamper detection |
| HMAC / asymmetric sign | Authenticity of writer (not implemented in v1) |
| WORM storage | Immutability at rest (operational — not code) |

Roadmap may add signed packages; current design is intentionally local-first and simple.

---

## Related documents

- [audit_chain_of_custody.md](audit_chain_of_custody.md)
- [adr/0004-audit-hash-chain-design.md](adr/0004-audit-hash-chain-design.md)
- [risk-control-framework.md](risk-control-framework.md) — CTRL-010
- [anti-code-paste-defense.md](anti-code-paste-defense.md) — Q9
