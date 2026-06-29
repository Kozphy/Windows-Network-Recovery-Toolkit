# Rollback strategy (preview-first)

**Status:** Portfolio prototype — preview and audit only by default.

**Positioning:** Rollback planning supports **reversible remediation narratives** and governance audit. It is **not** a guarantee of safety, full state restoration, or compromise recovery.

---

## Rollback model

Every policy-gated remediation path that may mutate endpoint state should produce this **six-part preview package** before any live change:

| # | Artifact | Purpose |
|---|----------|---------|
| 1 | **Pre-change evidence snapshot** | Read-only capture of proxy/registry posture at decision time |
| 2 | **Proposed mutation preview** | Forward change described as dry-run steps (no execution) |
| 3 | **Human approval token** | Cryptographic gate — operator must present matching token |
| 4 | **Reversible action record** | Links snapshot, action id, and confirmation requirements |
| 5 | **Rollback preview** | Steps to restore captured values (registry restore + validate) |
| 6 | **Rollback audit record** | Append-only JSONL row for preview / blocked execute attempts |

```text
Evidence ──► Pre-change snapshot
                    │
Policy ALLOW ──► Mutation preview ──► Approval token ──► Reversible action record
                    │
                    └──► Rollback preview ──► Audit record (preview_only)
```

---

## Code locations

| Component | Path |
|-----------|------|
| Preview package builder | `src/platform_core/remediation/rollback.py` |
| Planner integration | `src/platform_core/remediation/planner.py` |
| `RemediationPreview.rollback_preview` | `platform_core/models.py` |
| Classic preview builder | `platform_core/policy/classic.py` |
| Platform API LKG preview | `platform_core/product_contract.py` (`POST /platform/rollback/preview`) |
| Live proxy-guard rollback (opt-in, separate) | `src/proxy_guard/rollback.py` |

Canonical helpers:

- `capture_pre_change_snapshot()` — read-only snapshot
- `build_proposed_mutation_preview()` — forward change preview
- `build_rollback_preview_package()` — assembles all six artifacts
- `build_rollback_audit_record()` / `append_rollback_audit_record()` — audit JSONL
- `can_execute_rollback()` / `attempt_rollback_execute()` — **always blocked** in platform core by default

---

## Default behavior

1. **Dry-run is the default** for remediation and rollback packages (`dry_run: true`).
2. **No live rollback** in `src/platform_core/remediation/rollback.py` — even with valid approval token and typed phrase `RESTORE_PROXY_LKG`, `can_execute_rollback()` returns `live_rollback_executor_disabled_preview_only`.
3. **Typed confirmation** is required before any hypothetical live path (`ROLLBACK_CONFIRMATION_PHRASE`).
4. **Audit append** on preview generation and execute attempts (`logs/rollback_audit.jsonl` or caller-provided path).

Operator-run live restores (e.g. `python -m src proxy-rollback`, `proxy-guard --auto-rollback`) remain **separate, opt-in CLI surfaces** with their own confirmation phrases and are not invoked by the platform preview pipeline.

---

## Workflow

### 1. Generate remediation preview

```python
from src.platform_core.remediation.planner import plan_proxy_drift_remediation

plan = plan_proxy_drift_remediation(incident_id="inc-1", dry_run=True)
package = plan["rollback_preview"]
```

### 2. Review structured fields

`RemediationPreview` (API/CLI) may include:

- `rollback_plan` — human-readable string (legacy)
- `rollback_preview` — structured `RollbackPreviewFields` with snapshot, steps, limitations

### 3. Append audit (optional explicit call)

```python
from src.platform_core.remediation.rollback import append_rollback_audit_record

append_rollback_audit_record(package["rollback_audit_record"])
```

### 4. Attempt execute (blocked by default)

```python
from src.platform_core.remediation.rollback import attempt_rollback_execute

result = attempt_rollback_execute(package, dry_run=True)
assert result["executed"] is False
```

---

## Limitations (explicit non-claims)

Rollback preview **does not** guarantee:

- Restoration of unknown prior PAC, per-user policy, or machine-wide proxy settings not captured in the snapshot
- Resolution of endpoint compromise or malware-induced drift
- Idempotent success across all Windows builds and enterprise GPO overlays
- Safe automatic execution without human review of the full preview package

Captured snapshots reflect **observed values at capture time** only. Validation steps after rollback are **recommended**, not enforced, in the preview model.

Policy `ALLOW` or `PREVIEW_ONLY` is **not** a safety guarantee — rollback review and audit remain mandatory per [evidence_to_action_governance_model.md](evidence_to_action_governance_model.md).

---

## Tests

| Test file | Coverage |
|-----------|----------|
| `tests/platform_core/remediation/test_rollback_preview.py` | Six-part package, limitations, no execute without confirmation, audit append |
| `tests/platform_core/remediation/test_remediation_planner.py` | Planner dry-run + legacy rollback plan steps |
| `tests/test_remediation_preview.py` | Classic preview rollback copy |
| `tests/test_platform_product_contract.py` | API `/platform/rollback/preview` preview-only |

**No live mutation tests** in the platform rollback module — live restore behavior is covered separately under `tests/test_proxy_guard_*.py`.

---

## Related documentation

- [safety-model.md](safety-model.md)
- [security-review.md](security-review.md)
- [proxy_guard_rollback.md](proxy_guard_rollback.md) (opt-in live paths)
- [enterprise-hardening-roadmap.md](enterprise-hardening-roadmap.md) — Phase 8
