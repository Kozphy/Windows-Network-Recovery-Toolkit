# Domain event inventory (pre–kernel baseline)

**Status:** Historical inventory captured for the Level-1 domain event kernel vertical slice.  
**Not** a claim that every JSONL in the repo is migrated.

## Canonical custody (unified sink)

| Path | Writer | Verifier | Integrity |
|------|--------|----------|-----------|
| `.audit/canonical_custody.jsonl` | `append_domain_event` / `append_audit` / `append_custody_event` | `verify_domain_stream` via `audit verify` | Hash chain + tip `.tip.json` |
| `.audit/canonical_custody.tip.json` | `write_tip_anchor` | tip match in verify | Tip hash + record count |

Env override: `WNT_AUDIT_DIR` (default `.audit`). Tenant scope: `WNT_TENANT_ID` (default `local`).

## Legacy / dual-write operator logs (still written)

| Path | Entry point | Notes |
|------|-------------|-------|
| `logs/proxy_guardian.jsonl` | `src/proxy_drift/guardian.py` `_audit` | Dual-writes custody domain events |
| `logs/decision_audit.jsonl` | `src/cli.py` `_audit` | Dual-writes `decision.diagnosis` domain events |
| `logs/decision_feedback.jsonl` | `src/cli` feedback cmds | Not yet on domain kernel |
| `logs/proxy_guard.jsonl` | proxy-guard watch paths | Separate; not migrated this slice |
| `.audit/*.jsonl` soft-fail audits | `windows_network_toolkit/audit_store.py` | Soft-fail local audits |
| Other diagnostics JSONL | browser-diff, proxy-watch, etc. | Out of scope for this slice |

## Pre-kernel duplication

- Plain `src.logging.audit.append_jsonl` (no hash chain)
- `src.platform_core.audit.writer.append_audit` (`erp.audit.v1`)
- `append_custody_event` mapping guardian/proxy-fix into audit actions
- Multiple verify helpers (`verify_chain`, `verify_audit_with_tip`)

## Migration risks

| Risk | Mitigation in this slice |
|------|--------------------------|
| Existing `erp.audit.v1` files | Still chain-verify; envelope view via compat |
| Tests asserting `erp.audit.v1` schema on new writes | New writes are `wnrt.domain_event.v1`; AuditRecord API preserved |
| Soft-fail custody vs hard-fail diagnose | Guardian/diagnose catch exceptions; do not block ops |
| Tip required unexpectedly | CLI tip check only when `--check-tip` / `--require-tip` |

## Integrity model

1. Append under file lock  
2. `current_hash = SHA256(previous_hash + canonical_json(body_without_integrity_fields))`  
3. Refresh sibling tip anchor  
4. Verify: parse → schema gate → chain → optional tip  
