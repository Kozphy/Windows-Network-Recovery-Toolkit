# UAT Plan — User Acceptance Test Scenarios

**Platform:** Technology Risk & Control Analytics for Windows endpoints
**Scope:** Workflows supported by implemented or prototype code — not production fleet deployment

Format: **Given / When / Then / Expected Evidence / Pass-Fail**

---

## UAT-001 — Normal dead proxy detection (read-only)

| Field | Value |
|-------|-------|
| **Given** | Fixture `dead_proxy_60505.json` or live dead localhost proxy |
| **When** | Operator runs `python -m windows_network_toolkit proxy-status --fixture dead_proxy_60505.json` |
| **Then** | Classification indicates dead proxy path; `limitations[]` present |
| **Expected evidence** | JSON output with probe results; no registry mutation |
| **Pass** | Label consistent with DEAD_PROXY; dry-run unchanged |
| **Fail** | Missing limitations; registry mutated |

**Status:** **Implemented**

---

## UAT-002 — Remediation preview (default dry-run)

| Field | Value |
|-------|-------|
| **Given** | Enabled WinINET proxy toward dead localhost |
| **When** | `python -m windows_network_toolkit proxy-disable --dry-run true` |
| **Then** | Policy outcome PREVIEW_ONLY; diff shown; no apply |
| **Expected evidence** | Preview JSON; audit event with `confirmation_supplied: false` |
| **Pass** | `mutated: false` or equivalent |
| **Fail** | Registry changed without confirmation |

**Status:** **Implemented**

---

## UAT-003 — Gated apply with confirmation token

| Field | Value |
|-------|-------|
| **Given** | Operator intends live apply on Windows endpoint |
| **When** | `proxy-disable --dry-run false --confirm DISABLE_WININET_PROXY` (or equivalent API) |
| **Then** | Apply proceeds only with correct token; verify step runs |
| **Expected evidence** | Apply audit row; verification output |
| **Pass** | Token mismatch blocks; correct token applies + verifies |
| **Fail** | Wrong token applies; token string in audit log |

**Status:** **Implemented** (Windows live path)

---

## UAT-004 — Unsafe action prevention

| Field | Value |
|-------|-------|
| **Given** | Request for blocked action (process kill, firewall reset, adapter disable) |
| **When** | Policy evaluates blocked action |
| **Then** | Outcome BLOCK; no execution |
| **Expected evidence** | Policy JSON with BLOCK |
| **Pass** | CI `test_policy_safety_contract.py` passes |
| **Fail** | Any blocked action executes |

**Status:** **Implemented**

---

## UAT-005 — Malformed fixture input

| Field | Value |
|-------|-------|
| **Given** | Invalid or empty fixture JSON |
| **When** | Diagnose or purple validate with bad fixture |
| **Then** | Structured error; no partial mutation |
| **Expected evidence** | Error code/message; no custody gap |
| **Pass** | Fail fast with clear error |
| **Fail** | Silent success or crash without audit |

**Status:** **Implemented**

---

## UAT-006 — Audit chain verification

| Field | Value |
|-------|-------|
| **Given** | Existing `.audit/canonical_custody.jsonl` with tip |
| **When** | `python -m windows_network_toolkit audit verify .audit/canonical_custody.jsonl --check-tip` |
| **Then** | `verified: true` for intact chain |
| **Expected evidence** | Verify CLI JSON |
| **Pass** | Chain + tip match |
| **Fail** | Tampered line undetected |

**Status:** **Implemented** — see `tests/test_audit_contract.py`

---

## UAT-007 — Tampered audit detection

| Field | Value |
|-------|-------|
| **Given** | Custody JSONL with one altered hash |
| **When** | Audit verify runs |
| **Then** | Verification fails at break index |
| **Expected evidence** | `verified: false`, break location |
| **Pass** | Tamper detected |
| **Fail** | Altered chain passes |

**Status:** **Implemented** — `tests/platform_core/governance/test_hash_chained_audit.py`

---

## UAT-008 — Purple scenario validation (fixture)

| Field | Value |
|-------|-------|
| **Given** | Scenario `proxy-drift-001` with fixture |
| **When** | `python -m src.purple_team validate proxy-drift-001` |
| **Then** | Safety gate pass; schema valid |
| **Expected evidence** | Validate output JSON |
| **Pass** | validate exits 0 |
| **Fail** | Missing rollback or safety fields |

**Status:** **Prototype**

---

## UAT-009 — Purple full pipeline benchmark

| Field | Value |
|-------|-------|
| **Given** | All scenario fixtures |
| **When** | `python -m src.purple_team benchmark --no-evidence --json` |
| **Then** | Metrics emitted; no live mutation |
| **Expected evidence** | Benchmark JSON with P/R/F1 |
| **Pass** | CI eval-benchmarks job green |
| **Fail** | Pipeline DENIED unexpectedly or crash |

**Status:** **Prototype**

---

## UAT-010 — Degraded operation (audit soft-fail)

| Field | Value |
|-------|-------|
| **Given** | Read-only disk or unwritable audit dir |
| **When** | Remediation preview attempted |
| **Then** | Preview may succeed; custody write soft-fails with warning |
| **Expected evidence** | Operator warning in output |
| **Pass** | No silent apply; limitation documented |
| **Fail** | Apply succeeds with zero audit attempt |

**Status:** **Implemented** behavior — document limitation R-015

---

## UAT-011 — Permission failure (non-admin)

| Field | Value |
|-------|-------|
| **Given** | Standard user without registry write |
| **When** | Live apply attempted |
| **Then** | Apply fails with clear error |
| **Expected evidence** | Error message; audit attempt |
| **Pass** | Fail closed |
| **Fail** | Partial registry write |

**Status:** **Implemented** (environment-dependent)

---

## UAT-012 — Post-remediation verification failure

| Field | Value |
|-------|-------|
| **Given** | Apply completed but proxy still enabled |
| **When** | `verify_proxy_disabled()` runs |
| **Then** | Verification reports failure |
| **Expected evidence** | Verify output FAIL |
| **Pass** | Operator alerted to retry / escalate |
| **Fail** | Success reported despite bad state |

**Status:** **Implemented**

---

## UAT execution checklist

| # | Scenario | Platform | Automatable |
|---|----------|----------|-------------|
| UAT-001 | Dead proxy detect | Any (fixture) | Yes — pytest |
| UAT-002 | Preview default | Windows / fixture | Yes — CI |
| UAT-003 | Gated apply | Windows live | Manual lab |
| UAT-004 | Blocked actions | Any | Yes — CI |
| UAT-006 | Audit verify | Any | Yes — CLI |
| UAT-009 | Purple benchmark | Any | Yes — CI |

Run automated slice:

```powershell
$env:PYTHONPATH = (Get-Location).Path
pytest -q tests/test_policy_safety_contract.py tests/test_audit_contract.py tests/purple_team
python -m src.purple_team benchmark --no-evidence --json
```
