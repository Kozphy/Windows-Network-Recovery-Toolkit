# Requirements

**Platform:** Technology Risk & Control Analytics for Windows endpoints
**Status:** Requirements trace to **Implemented**, **Prototype**, or **Planned** — see status column

---

## Functional requirements

| ID | Requirement | Status | Evidence |
|----|-------------|--------|----------|
| FR-001 | System shall collect WinINET/WinHTTP proxy configuration evidence | **Implemented** | `proxy_registry_collector.py`, `proxy-status` |
| FR-002 | System shall detect dead localhost proxy paths | **Implemented** | Classifier `DEAD_PROXY_CONFIG`, CTRL-001 |
| FR-003 | System shall classify incidents with explicit `limitations[]` | **Implemented** | Classification engine; CI safety contracts |
| FR-004 | System shall run mapped control tests per incident class | **Implemented** | `control_tests.py`, CTRL-001–010 |
| FR-005 | System shall contrast direct vs proxied network paths | **Implemented** | `proxy-health`, CTRL-008 |
| FR-006 | System shall produce remediation previews by default | **Implemented** | `dry_run=True` defaults |
| FR-007 | System shall require typed confirmation for registry apply | **Implemented** | `DISABLE_WININET_PROXY` token |
| FR-008 | System shall append hash-chained audit records | **Implemented** | `src/platform_core/audit/writer.py` |
| FR-009 | System shall verify audit chain integrity | **Implemented** | `audit verify --check-tip` |
| FR-010 | System shall verify post-remediation proxy state | **Implemented** | `verify_proxy_disabled()` |
| FR-011 | System shall run purple validation scenarios (fixture) | **Prototype** | `src/purple_team/pipeline.py` |
| FR-012 | System shall export governance committee reports | **Prototype** | `governance-report`, sample in `reports/` |
| FR-013 | System shall attribute registry writers without Sysmon | **Not supported** | Requires E13 / Procmon |
| FR-014 | System shall autonomously remediate without human gate | **Not supported** | Blocked by policy + safety |
| FR-015 | System shall detect malware | **Not supported** | Explicit non-claim |

---

## Non-functional requirements

| ID | Requirement | Status | Evidence |
|----|-------------|--------|----------|
| NFR-001 | **Reliability:** Read-only paths shall not mutate endpoint state | **Implemented** | Default CLI behavior |
| NFR-002 | **Security:** Blocked actions shall fail closed | **Implemented** | `BLOCKED_ACTIONS`, CI tests |
| NFR-003 | **Observability:** Actions shall emit structured JSON | **Implemented** | JSON-first CLI |
| NFR-004 | **Traceability:** Decisions shall link to audit records | **Implemented** | Custody writer |
| NFR-005 | **Maintainability:** Deterministic fixtures for CI | **Implemented** | `tests/fixtures/` |
| NFR-006 | **Testability:** Safety contracts in CI | **Implemented** | `ci.yml` eval + policy tests |
| NFR-007 | **Recoverability:** Rollback preview packages | **Implemented** | `rollback.py` preview |
| NFR-008 | **Performance:** Full pytest suite completes in CI | **Implemented** | ~12 min Linux + Windows jobs |
| NFR-009 | **Availability:** HA multi-region API | **Not supported** | Local/demo API only |

---

## Governance requirements

| ID | Requirement | Status | Evidence |
|----|-------------|--------|----------|
| GR-001 | High-risk registry mutations require human confirmation | **Implemented** | Confirmation tokens |
| GR-002 | Decisions shall retain supporting evidence references | **Implemented** | Governance envelope |
| GR-003 | Overrides shall be logged (not token values) | **Implemented** | `confirmation_supplied` bool |
| GR-004 | Failures shall fail safely (no silent apply) | **Implemented** | Policy BLOCK outcomes |
| GR-005 | Classification shall not accuse without proof tier | **Implemented** | CTRL-006, CI language tests |
| GR-006 | AI shall not authorize execution | **Implemented** | ADR-0006; preview_only authority |
| GR-007 | Purple live mutation requires lab safety gate | **Prototype** | `PURPLE_TEAM_LAB_ONLY` |
| GR-008 | Formal regulatory attestation | **Not supported** | Management info only |

---

## Requirement traceability

```text
FR-001..005  →  Evidence collection + detection  →  tests/test_proxy_*
FR-006..007  →  Policy + remediation             →  tests/test_policy_safety_contract.py
FR-008..009  →  Audit                            →  tests/test_audit_contract.py
FR-011       →  Purple                           →  tests/purple_team/
GR-001..006  →  Governance                       →  tests/test_*_contract.py
```

UAT scenarios: [uat-plan.md](uat-plan.md)
