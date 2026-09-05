# Risk Register

**Platform:** Technology Risk & Control Analytics for Windows endpoints
**Status:** Portfolio demonstration register — **not** a production GRC export or formal risk acceptance record
**Legacy copy:** [risk_register.md](risk_register.md) · **Controls:** [control-matrix.md](control-matrix.md)

Ordinal likelihood and impact (1–5) — **not calibrated probabilities**.

---

## Register

| Risk ID | Risk | Cause | Impact | Likelihood | Mitigation | Residual Risk | Control IDs |
|---------|------|-------|--------|------------|------------|---------------|-------------|
| R-001 | Dead WinINET localhost proxy breaks browser egress | Stale dev proxy, crashed listener, drift | Productivity loss, repeat tickets | 4 | CTRL-001, preview remediation | Medium | CTRL-001, 008, 009 |
| R-002 | False security escalation (malware narrative) | Listener without writer proof | Wrong investigation path, reputational harm | 3 | CTRL-006, limitations[], CI language tests | Medium | CTRL-004, 006 |
| R-003 | TLS path mismatch misread as confirmed MITM | Path contrast without full proof | Over-reaction, false incident | 2 | Proof tier gates, `POSSIBLE_MITM_RISK` label | Medium–High | CTRL-008 |
| R-004 | Unsafe automated registry mutation | Bypass dry-run or policy regression | Unauthorized config change | 2 | BLOCKED_ACTIONS, CI safety contracts | Low (if CI green) | CTRL-009 |
| R-005 | Audit chain break or rewrite | Manual file edit, disk failure | Evidence inadmissible for committee | 3 | Hash chain + tip verify | Medium | CTRL-010 |
| R-006 | False negative — drift undetected | Incomplete telemetry, wrong fixture | Delayed remediation | 3 | Guardian watch, purple benchmarks | Medium | CTRL-007, purple |
| R-007 | False positive — benign flagged | Heuristic classifier limits | Unnecessary remediation preview | 3 | Human review, purple FPR metrics | Medium | Purple eval |
| R-008 | Corrupted or incomplete evidence bundle | Partial collector failure | Wrong classification | 3 | `limitations[]`, ERROR_INSUFFICIENT_DATA | Medium | FR-003 |
| R-009 | Stale configuration snapshot | Time drift between collect and apply | Apply wrong fix | 3 | Re-collect before apply; verify step | Medium | FR-010 |
| R-010 | Privilege failure on remediation | Non-admin operator | Failed apply, partial state | 3 | Clear error + audit; no silent partial | Medium | FR-007 |
| R-011 | External dependency failure (Sysmon absent) | Writer proof requested without E13 | Incomplete attribution | 4 | NOT_TESTED / tier cap | High for attribution | CTRL-004 |
| R-012 | Unsafe purple live mutation | Safety gate bypass | Unintended endpoint change | 2 | Deny-by-default gate, fixture-only CI | Low in CI | GR-007 |
| R-013 | Incomplete telemetry in fleet | No signed agent at scale | Blind spots | 4 | Fleet gap documented | High at scale | NFR planned |
| R-014 | Model / AI uncertainty (if LLM used) | Hallucinated explanation | Misleading narrative | 2 | AI explanation-only; no execution authority | Low | GR-006 |
| R-015 | Unauthorized override without audit | Audit soft-fail on disk error | Missing custody record | 2 | Soft-fail documented; monitor disk | Medium | FR-008 |

---

## Detailed entries

### R-004 — Unsafe automated registry mutation

| Field | Value |
|-------|-------|
| **Cause** | Policy regression, operator bypasses preview |
| **Impact** | Control failure; potential outage |
| **Mitigation** | `tests/test_policy_safety_contract.py`, default dry-run, blocked actions |
| **Verification** | CI must pass before merge |
| **Status** | Mitigated in codebase — residual depends on deployment discipline |

### R-005 — Audit chain integrity

| Field | Value |
|-------|-------|
| **Cause** | Full-file rewrite without tip update |
| **Impact** | Cannot prove decision history |
| **Mitigation** | `--check-tip`; internal audit verifies before export |
| **Limitation** | Local tip is not WORM — see [audit-custody.md](audit-custody.md) |

### R-011 — Writer attribution without Sysmon

| Field | Value |
|-------|-------|
| **Cause** | E13 telemetry not deployed |
| **Impact** | Cannot prove registry writer |
| **Mitigation** | Cap proof tier; prohibit causal language |
| **Status** | **Accepted residual** in default portfolio deployment |

---

## Risk treatment summary

| Treatment | Risks |
|-----------|-------|
| **Mitigate** | R-001, R-004, R-005, R-006 (partial) |
| **Accept** | R-011 (without Sysmon), R-013 (fleet scale) |
| **Avoid** | R-012 (live purple in CI — use fixtures) |
| **Transfer** | None claimed (no insurance / vendor attestation) |

---

## Do not claim

- Zero residual risk
- Regulatory sign-off
- Production incident counts prevented
