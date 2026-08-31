# Decision Model

**Platform:** Technology Risk & Control Analytics for Windows endpoints
**Normative principles:** [evidence_to_action_governance_model.md](evidence_to_action_governance_model.md)
**Policy implementation:** `src/platform_core/policy/engine.py` · `windows_network_toolkit/safety.py`

---

## Pipeline overview

```text
Input / Telemetry / Fixtures
          ↓
Normalization (evidence events, tiers T0–T5)
          ↓
Evidence Generation (collectors, probes, HAR/TLS contrast)
          ↓
Detection / Classification (12+ proxy labels, purple DET-* rules)
          ↓
Control Evaluation (CTRL-001–010, PASS/FAIL/PARTIAL/NOT_TESTED)
          ↓
Risk Classification (ordinal confidence + limitations[])
          ↓
Decision Policy (BLOCK | PREVIEW_ONLY | REQUIRE_HUMAN_APPROVAL | ALLOW)
          ↓
      ┌───────────┴───────────┐
      │                       │
 Auto (read-only)      Human Review / Confirmation
      │                       │
      └───────────┬───────────┘
                ↓
         Execution (preview or gated apply)
                ↓
         Verification (post-conditions)
                ↓
         Audit Record (hash-chained JSONL)
                ↓
         Reporting (governance export, KPIs)
```

Purple Team overlay:

```text
Simulate (fixture) → Observe → Detect → Respond (preview) → Verify → Measure
```

---

## Decision points

### DP-1: Evidence collection

| Field | Value |
|-------|-------|
| **Inputs** | Registry reads, netstat, HTTPS probes, optional Sysmon/Procmon imports |
| **Rules** | Read-only by default; fixture inject for CI |
| **Outputs** | `EvidenceEvent`, probe results, raw collector payloads |
| **Confidence** | Observation tier (T0–T2) until proof checks run |
| **Failure behavior** | Partial evidence with `limitations[]`; no silent success |
| **Escalation** | Operator collects supplemental telemetry |
| **Override** | `--fixture` for deterministic replay (documented) |
| **Evidence retained** | Collector output in diagnose bundle; audit append |

**Status:** **Implemented**

---

### DP-2: Classification

| Field | Value |
|-------|-------|
| **Inputs** | Normalized evidence, transition state, HAR/TLS contrast |
| **Rules** | `src/platform_core/classification/engine.py`; no `MALWARE_DETECTED` labels |
| **Thresholds** | Proof ladder T0–T5; `--proof` flag raises bar |
| **Outputs** | Label (e.g. `DEAD_PROXY_CONFIG`), confidence (ordinal), `limitations[]` |
| **Failure behavior** | `ERROR_INSUFFICIENT_DATA` / `INSUFFICIENT_BROWSER_EVIDENCE` |
| **Escalation** | Human triage for `UNKNOWN_LOCAL_PROXY`, `POSSIBLE_MITM_RISK` |
| **Override** | Human review queue (platform API); no auto-downgrade of limitations |
| **Evidence retained** | Classification JSON in diagnose output + audit |

**Status:** **Implemented**

---

### DP-3: Control evaluation

| Field | Value |
|-------|-------|
| **Inputs** | Incident class, evidence bundle |
| **Rules** | `windows_network_toolkit/control_tests.py` |
| **Outputs** | Per-control PASS/FAIL/PARTIAL/NOT_TESTED |
| **Failure behavior** | FAIL documented in governance report — not auto-remediated |
| **Escalation** | Risk owner reviews CTRL failure interpretation table |
| **Evidence retained** | Control test results in report + audit |

**Status:** **Implemented**

---

### DP-4: Policy gate

| Field | Value |
|-------|-------|
| **Inputs** | Requested action, evidence tier, `dry_run` flag, operator context |
| **Rules** | `evaluate()` in policy engine; `BLOCKED_ACTIONS` registry |
| **Outputs** | `BLOCK`, `PREVIEW_ONLY`, `REQUIRE_HUMAN_APPROVAL`, `ALLOW` |
| **Failure behavior** | **Fail closed** — blocked actions never execute |
| **Escalation** | Approver supplies confirmation token |
| **Override** | Typed token (e.g. `DISABLE_WININET_PROXY`); logged as bool only |
| **Evidence retained** | Policy decision JSON; `confirmation_supplied: true/false` in custody |

**Status:** **Implemented**

---

### DP-5: Remediation execution

| Field | Value |
|-------|-------|
| **Inputs** | Preview ID, `--dry-run`, confirmation phrase |
| **Rules** | Default `dry_run=True`; Windows-only guards |
| **Outputs** | Preview diff or apply result + rollback snapshot |
| **Failure behavior** | Block on token mismatch; soft-fail audit write |
| **Verification** | `verify_proxy_disabled()` post-apply |
| **Evidence retained** | Remediation audit events; rollback package |

**Status:** **Implemented** (preview + gated apply); browser repair apply **Prototype** (blocked stub)

---

### DP-6: Purple response (fixture)

| Field | Value |
|-------|-------|
| **Inputs** | Scenario YAML, fixture path, safety gate evaluation |
| **Rules** | `src/purple_team/safety/gate.py` — deny-by-default |
| **Outputs** | Pipeline state machine → COMPLETE / DENIED |
| **Failure behavior** | SAFETY_DENIED; no live mutation in CI |
| **Verification** | `src/purple_team/verification/` post-conditions |
| **Evidence retained** | Evidence bundle + benchmark metrics |

**Status:** **Prototype** (fixture-driven)

---

## Policy outcomes vs safety

| Policy says | Safety still requires |
|-------------|----------------------|
| `ALLOW` | Dry-run unless `--dry-run false` + token |
| `PREVIEW_ONLY` | No registry write |
| `REQUIRE_HUMAN_APPROVAL` | Explicit approver action |
| `BLOCK` | No execution path |

CI enforces: policy ALLOW ≠ safety guarantee (`tests/test_policy_not_safety.py`).

---

## Audit record schema (custody)

Hash-chained records include (see `docs/audit-custody.md`):

```json
{
  "schema_version": "audit_record.v1",
  "timestamp_utc": "...",
  "action_type": "PROXY_REMEDIATION_PREVIEW",
  "actor": "operator_cli",
  "resource": "wininet_proxy",
  "decision": "PREVIEW_ONLY",
  "confirmation_supplied": false,
  "previous_hash": "...",
  "current_hash": "...",
  "correlation_id": "..."
}
```

**Not stored:** confirmation token strings, secrets, credentials.

---

## Decision authority summary

| Decision | Automated | Human required |
|----------|-----------|----------------|
| Collect evidence | Yes | No |
| Classify | Yes | Review if ambiguous |
| Run control tests | Yes | Interpret FAIL |
| Preview remediation | Yes | No |
| Apply registry mutation | No | Yes — typed token |
| Purple live mutation | No | Yes — lab token + safety gate |
| Export to committee | No | Yes — verify audit chain first |
