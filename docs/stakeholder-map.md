# Stakeholder Map

**Platform:** Technology Risk & Control Analytics for Windows endpoints
**Status:** Reference implementation / portfolio prototype — not deployed enterprise production software
**Related:** [system-boundary.md](system-boundary.md) · [decision-model.md](decision-model.md) · [control-matrix.md](control-matrix.md)

---

## Purpose

This map defines who cares about endpoint proxy drift, reliability failures, and control validation — and what evidence each role needs to make defensible decisions.

Only stakeholders supported by the current repository are included.

---

## Stakeholder summary

| Stakeholder | Primary goal | Key decisions | Evidence consumed | Risks cared about |
|-------------|--------------|---------------|-------------------|-------------------|
| **IT Operations / Endpoint Support** | Restore browser and app connectivity quickly | Triage vs escalate; preview remediation | `proxy-status`, `diagnose`, operator incident card | Extended outage, repeat incidents, unsafe registry edits |
| **Platform / Endpoint Engineering** | Maintain predictable network stack behavior | Prioritize fixes; approve automation scope | Control tests, replay benchmarks, CI contracts | Config drift, flapping proxy, untested remediation |
| **Security Operations** | Distinguish reliability issues from security hypotheses | Escalate attribution gaps; avoid false accusations | Listener attribution, TLS path contrast, `limitations[]` | False positives, missed writer attribution, narrative overreach |
| **Technology Risk / GRC** | Assess control effectiveness and residual risk | Accept residual risk; prioritize control improvements | Control matrix CTRL-001–010, risk register, governance reports | Control failure, unverified remediation, weak audit trail |
| **Internal Audit / Risk Advisory** | Trace decisions to evidence | Sample control tests; verify audit integrity | Hash-chained JSONL, `audit verify`, governance envelope | Non-replayable decisions, broken custody chain, silent mutations |
| **Compliance / Change Advisory** | Ensure changes are authorized and traceable | Approve remediation windows | Remediation preview, confirmation token audit (bool only) | Unauthorized config change, missing rollback plan |
| **Product / Portfolio Owner** | Demonstrate measurable control-validation capability | Scope roadmap; define acceptance criteria | Purple benchmark metrics, UAT scenarios, KPI framework | Over-claiming capabilities; portfolio misrepresentation |
| **Management / Risk Committee** | Understand incident volume and control posture | Allocate budget; set tolerance | KPI rollups, `analytics-summary`, sample governance report | Recurring dead-proxy incidents, rising exception rate |
| **System Administrator (operator)** | Execute approved remediation safely | Apply vs defer; supply confirmation token | Dry-run preview, rollback snapshot, verification output | Irreversible registry change without preview |
| **Approver (human gate)** | Authorize high-impact mutations | Approve `proxy-disable` apply | Preview package, policy outcome, evidence tier | Policy bypass, missing human review |

---

## Detailed profiles

### IT Operations / Endpoint Support

- **Goals:** Reduce mean time to diagnose dead localhost proxies and WinINET/WinHTTP mismatches.
- **Responsibilities:** Run read-only diagnostics first; escalate when writer attribution is unknown.
- **Decisions:** Preview remediation vs manual browser reset vs escalate to Security.
- **Evidence needed:** Classification label, proof tier, control test PASS/FAIL, remediation preview JSON.
- **Risks:** Ad-hoc registry resets without audit; treating correlation as root cause.

**Implemented support:** `python -m windows_network_toolkit proxy-status`, `diagnose`, `proxy-disable --dry-run true`; `python -m src operator-incident`.

---

### Security Operations

- **Goals:** Triage unknown localhost listeners without malware verdicts.
- **Responsibilities:** Collect Sysmon E13 or Procmon when writer proof is required.
- **Decisions:** Investigate further vs close as reliability incident.
- **Evidence needed:** `proxy-owner`, attribution tier, prohibited-language checks in governance envelope.
- **Risks:** Accusatory classification; process-on-port mistaken for registry writer.

**Implemented support:** CTRL-004, CTRL-006; classifiers cap language at `POSSIBLE_MITM_RISK` (not confirmed MITM).

---

### Technology Risk / GRC

- **Goals:** Map incidents to control objectives and residual risk.
- **Responsibilities:** Maintain control test cadence; review override patterns.
- **Decisions:** Accept residual risk; request additional telemetry.
- **Evidence needed:** [control-matrix.md](control-matrix.md), [risk-register.md](risk-register.md), governance reports.
- **Risks:** Treating portfolio demo as SOC 2 attestation; ignoring `limitations[]`.

**Implemented support:** Six mature control tests; governance report CLI; Power BI star-schema export (blueprint).

---

### Internal Audit

- **Goals:** Reconstruct who decided what, using which evidence.
- **Responsibilities:** Verify hash chain before consuming exports.
- **Decisions:** Rely on audit trail vs request supplemental evidence.
- **Evidence needed:** `.audit/canonical_custody.jsonl`, tip anchor, replay determinism tests.
- **Risks:** Assuming append-only JSONL is WORM; token values in logs (explicitly **not** stored).

**Implemented support:** `audit verify --check-tip`; custody mapping in `src/platform_core/audit/custody.py`.

---

### Approver / Operator

- **Goals:** Apply remediation only when preview and policy allow.
- **Responsibilities:** Supply typed confirmation token for live registry mutation.
- **Decisions:** Apply `DISABLE_WININET_PROXY` vs defer.
- **Evidence needed:** Preview diff, rollback snapshot, post-apply verification.
- **Risks:** Bypassing dry-run default; applying without verification.

**Implemented support:** `CONFIRMATION_TOKENS` in `windows_network_toolkit/safety.py`; `verify_proxy_disabled()` in `src/proxy_guard/verification.py`.

---

## Stakeholders explicitly out of scope

| Role | Why excluded |
|------|----------------|
| External regulator | No regulatory filing or attestation workflow |
| End user / employee | No self-service portal in v1 |
| SOC analyst (full EDR) | Not an EDR replacement — see [system-boundary.md](system-boundary.md) |

---

## Capability status legend

| Label | Meaning |
|-------|---------|
| **Implemented** | Runnable CLI/API with tests |
| **Prototype** | Fixture-driven or preview-only |
| **Planned** | Documented roadmap only |
| **Not supported** | Must not be claimed |

All stakeholder workflows above map to **Implemented** or **Prototype** paths documented in [requirements.md](requirements.md).
