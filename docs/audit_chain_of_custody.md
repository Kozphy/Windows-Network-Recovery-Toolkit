# Audit Chain of Custody

Append-only JSONL audit with hash chaining.

## Fields

Each record includes:

- `previous_hash` — prior record chain tip (or `genesis`)
- `current_hash` — SHA-256 of canonical body + previous hash
- `signature_status` — `hash_chained`

Implementation: `src/platform_core/audit/writer.py`, `src/platform_core/governance/chain_of_custody.py`

## Verify

```powershell
python -m toolkit audit verify logs/canonical_decision_audit.jsonl
```

Returns `verified: true` when chain intact; `false` on tamper or break.

## Doctrine

Audit proves **what was decided and when** — not that causation was proven.
