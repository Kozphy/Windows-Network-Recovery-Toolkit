# Failure Taxonomy

**Platform:** Technology Risk & Control Analytics for Windows endpoints
**Purple research taxonomy:** [research/failure_taxonomy.md](../research/failure_taxonomy.md)
**Related:** [decision-model.md](decision-model.md) · [risk-register.md](risk-register.md)

---

## Classification

Failures are grouped so operators and auditors know **what broke**, **how it is detected**, **expected behavior**, and **what evidence is produced**.

Principle: **fail safe** — prefer BLOCK / ERROR with limitations over silent success.

---

## F1 — Input Failure

| Field | Detail |
|-------|--------|
| **Examples** | Invalid fixture, missing file, malformed JSON, unreachable registry key |
| **Detection** | Parser errors; Pydantic validation; CLI exit ≠ 0 |
| **Expected behavior** | Fail fast; no mutation; no partial classify |
| **Retry** | Fix input; re-run command |
| **Escalation** | Operator / test author |
| **Evidence** | Error message; optional audit `INPUT_REJECTED` |

**Status:** **Implemented**

---

## F2 — Evidence Collection Failure

| Field | Detail |
|-------|--------|
| **Examples** | netstat timeout, probe failure, browser DB locked |
| **Detection** | Collector exceptions; partial bundle flags |
| **Expected behavior** | Continue with `limitations[]`; may yield `ERROR_INSUFFICIENT_DATA` |
| **Retry** | Re-run collect; close browser if DB locked |
| **Escalation** | IT Ops |
| **Evidence** | Partial diagnose JSON with limitations |

**Status:** **Implemented**

---

## F3 — Detection / Classification Failure

| Field | Detail |
|-------|--------|
| **Examples** | False negative (missed drift); false positive (benign flagged) |
| **Detection** | Purple benchmark; fixture regression; human review |
| **Expected behavior** | Document uncertainty; never upgrade to malware label |
| **Retry** | Supplement telemetry (Sysmon); re-classify |
| **Escalation** | Security triage / Risk |
| **Evidence** | Classification + limitations; purple metrics |

**Status:** **Implemented** (detection); FNR/FPR measured in **Prototype** purple bench

---

## F4 — Policy Evaluation Failure

| Field | Detail |
|-------|--------|
| **Examples** | Policy engine exception; unknown action type |
| **Detection** | Exception handler; CI policy tests |
| **Expected behavior** | **Fail closed** → BLOCK |
| **Retry** | Fix config; patch policy registry |
| **Escalation** | Platform Engineering |
| **Evidence** | BLOCK outcome; test failure in CI |

**Status:** **Implemented**

---

## F5 — Authorization Failure

| Field | Detail |
|-------|--------|
| **Examples** | Wrong confirmation token; DEMO_MODE; purple safety deny |
| **Detection** | Token mismatch; `evaluate_safety()` DENY |
| **Expected behavior** | No apply; audit `*_blocked` event |
| **Retry** | Operator supplies correct token or escalates |
| **Escalation** | Approver |
| **Evidence** | `confirm_token_mismatch`; `SAFETY_DENIED` pipeline state |

**Status:** **Implemented**

---

## F6 — Remediation Failure

| Field | Detail |
|-------|--------|
| **Examples** | Registry write denied; insufficient privileges |
| **Detection** | OS error; non-zero exit |
| **Expected behavior** | No claim of success; audit failure row |
| **Retry** | Elevated session; rollback preview if partial |
| **Escalation** | IT Ops |
| **Evidence** | Remediation audit + error detail |

**Status:** **Implemented**

---

## F7 — Verification Failure

| Field | Detail |
|-------|--------|
| **Examples** | Proxy still enabled after apply; purple post-condition miss |
| **Detection** | `verify_proxy_disabled()`; purple verification stage |
| **Expected behavior** | Report FAIL; do not close incident |
| **Retry** | Re-run remediation or manual fix |
| **Escalation** | Operator + Risk if recurring |
| **Evidence** | Verification JSON; purple VERIFICATION_FAILURE |

**Status:** **Implemented** (proxy); **Prototype** (purple)

---

## F8 — Audit Logging Failure

| Field | Detail |
|-------|--------|
| **Examples** | Disk full; permission denied on `.audit/` |
| **Detection** | Soft-fail warning in writer |
| **Expected behavior** | Operation may complete but **limitation documented** — R-015 |
| **Retry** | Fix disk permissions; re-run verify |
| **Escalation** | Internal Audit if export needed |
| **Evidence** | Gap in chain; verify fails |

**Status:** **Implemented** (soft-fail by design)

---

## F9 — Rollback Failure (Purple / remediation)

| Field | Detail |
|-------|--------|
| **Examples** | Fixture cleanup stage fails |
| **Detection** | Purple ROLLBACK_FAILURE category |
| **Expected behavior** | Pipeline not COMPLETE; operator alerted |
| **Retry** | Manual fixture reset |
| **Escalation** | Lab operator |
| **Evidence** | Purple pipeline state + bundle |

**Status:** **Prototype**

---

## Failure response matrix

| Class | Fail open? | Default |
|-------|------------|---------|
| F1 Input | No | Reject |
| F2 Evidence | Partial OK | Limitations |
| F3 Detection | No | Conservative label |
| F4 Policy | No | BLOCK |
| F5 Auth | No | DENY |
| F6 Remediation | No | Error |
| F7 Verification | No | FAIL |
| F8 Audit | Warn | Soft-fail + document |
| F9 Rollback | No | Halt pipeline |

---

## CI enforcement map

| Failure class | Test / job |
|---------------|------------|
| F4, F5 | `tests/test_policy_safety_contract.py` |
| F3 language | `tests/test_proxy_classifier_safety_contract.py` |
| F8 chain | `tests/test_audit_contract.py` |
| F3 purple | `tests/purple_team/`, CI benchmark |
