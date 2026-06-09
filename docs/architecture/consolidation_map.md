# Consolidation Map

| Legacy path | Canonical path | Shim | Status |
|-------------|----------------|------|--------|
| `platform_core/evidence_model.py` | `src/platform_core/evidence/tiers.py` | Import guards from canonical | Migrated logic |
| `platform_core/policy/engine.py` | `src/platform_core/policy/engine.py` | Re-export wrapper planned | Parallel |
| `platform_core/audit.py` | `src/platform_core/audit/writer.py` | Legacy remains | Dual-write optional |
| `src/platform/models.py` | `src/platform_core/contracts.py` | `src/platform` re-exports | Shim |
| `src/platform/replay.py` | `src/platform_core/replay/certifier.py` | Both active | Shim |
| `backend/decision_intelligence/` | `src/platform_core/pipeline.py` | Not yet | Debt |
| `windows_network_toolkit/pipeline.py` | `src/platform_core/pipeline.py` | WNT calls canonical | Migrating |
| `proxy_guard/` (root) | `src/proxy_guard/` | Duplicate trees | Keep both |
| `platform_core/decision_platform/` | `src/platform/` MDP adapters | Deprecated docstring | Fixture MDP |

## Removal criteria

1. All imports use canonical path or documented shim.
2. Golden replay tests pass on canonical pipeline only.
3. No duplicate policy vocabulary in new code paths.
4. Audit JSONL schema version `erp.audit.v1` stable for 2 releases.
