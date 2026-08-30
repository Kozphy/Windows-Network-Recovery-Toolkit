# Proxy Proof Ladder — T0 through T7

**Status:** Normative claim-strength and assurance ladder for WinINET proxy investigations  
**Modules:** `evidence_schema.EvidenceTier`, `src/platform_core/governance/proof_tier.py`, `proxy_state_machine.build_proxy_evidence_event`, `proof.py`  
**Principle:** Each rung adds evidence or verification strength. **Proof tier never grants execution authority.**

---

## Ladder overview

```text
T7 INDEPENDENT_VERIFICATION  Separate verifier validates bundle + hash chain + deterministic replay
T6 CONTROLLED_VALIDATION     Controlled change → failure → rollback → recovery is repeatable
T5 GOVERNANCE_PROOF          Human-confirmed action + verified audit chain
T4 WRITER / OPERATOR PROOF   Writer telemetry or explicitly recorded operator confirmation
T3 PATH / BEHAVIOR EVIDENCE  Direct vs proxy probes and reproducible behavior
T2 RUNTIME_CORROBORATION     Listener/process/co-temporal runtime evidence
T1 STATE EVIDENCE            WinINET/WinHTTP configuration read
T0 OBSERVATION               Unstructured note or uncorroborated signal
```

**Rules:**

1. Never skip rungs in an audit narrative.
2. Never describe correlation as causation.
3. T6 supports only the bounded mechanism actually tested.
4. T7 means independently verifiable evidence, **not certainty**.
5. `proof_tier != execution_authority`; policy and human approval remain separate.

---

## T0 — Observation

A fact recorded without structured normalization or corroboration.

**Examples:** operator note, raw log line, screenshot.  
**Proves:** something was observed or recorded.  
**Does not prove:** configuration truth, path behavior, writer identity, causation, or remediation safety.

## T1 — State evidence

Structured WinINET/WinHTTP configuration at a point in time.

**Example:** `ProxyEnable=1`, `ProxyServer=127.0.0.1:59081`.  
**Allowed:** "WinINET points to localhost port 59081."  
**Blocked:** "Dead proxy confirmed" without path evidence.

## T2 — Runtime corroboration

Runtime evidence such as listener state, process/port correlation, or stack contrast.

**Allowed:** "Process X is correlated with the configured localhost port."  
**Blocked:** "Process X wrote the registry" without writer telemetry.

## T3 — Path / behavioral evidence

Structured direct-vs-proxy connectivity contrast or reproducible behavior.

**Example:** direct HTTPS succeeds while proxy path fails.  
**Supports:** a bounded network-impact hypothesis.  
**Blocked:** malware, intent, or universal-causation claims.

## T4 — Writer / operator proof

Strong attribution or explicitly recorded operator action. Depending on the evidence surface this may include Sysmon Event ID 13 / Procmon registry-write evidence or an operator-confirmed action recorded by the governance resolver.

**Important:** writer identity proves who wrote a value; it does not prove malicious intent.

## T5 — Governance proof

Human-confirmed action with verified audit-chain evidence.

**Required by the governance resolver:** operator confirmation plus verified audit chain/replay certification.  
**Allowed:** "Operator confirmed the policy action and the audit chain verifies."  
**Blocked:** "The action is therefore safe in every environment" or a formal audit opinion.

---

## T6 — Controlled validation

### Definition

A controlled, isolated or fixture-based experiment validates the bounded failure mechanism:

```text
baseline
  ↓
controlled change
  ↓
failure reproduced
  ↓
rollback
  ↓
recovery verified
  ↓
repeat experiment
```

### Resolver requirements

All must be true:

- `isolated_or_fixture_based`
- `change_applied`
- `failure_reproduced`
- `rollback_applied`
- `recovery_verified`
- `repeatable`
- T5 governance proof is already satisfied

### What T6 means

T6 supports the statement that **under the tested conditions**, the controlled change is a reproducible causal mechanism for the observed failure and rollback restores the tested behavior.

### What T6 does NOT mean

- The same mechanism explains every similar incident.
- Intent is known.
- Malware or compromise is proven.
- Execution is automatically authorized.

---

## T7 — Independent verification

### Definition

A separate verifier can validate evidence integrity and reproduce the decision from the evidence bundle without trusting the original conclusion.

```text
Evidence bundle
   ↓
independent verifier
   ↓
schema / bundle verification
   ↓
hash-chain verification
   ↓
deterministic replay
   ↓
classification reproduced
```

### Resolver requirements

All must be true:

- T6 controlled validation is already satisfied
- `independent_verifier`
- `evidence_bundle_verified`
- `hash_chain_verified`
- `deterministic_replay_verified`
- `classification_reproduced`

### What T7 means

The evidence package and decision are independently reproducible at the highest assurance tier currently modeled by the portfolio.

### What T7 does NOT mean

- 100% certainty
- formal audit attestation
- malware/compromise verdict
- malicious intent
- automatic remediation authority

---

## Safety invariant — proof is not permission

Even T7 can produce:

```text
proof_tier: T7_INDEPENDENT_VERIFICATION
policy: PREVIEW_ONLY
human_approval: REQUIRED
execution_authority: BLOCKED
```

This is intentional. Evidence strength, policy permission, coordination status, and execution authority are separate dimensions.

---

## Suspicious / MITM classifications

`POSSIBLE_MITM_RISK` and `SUSPICIOUS_PROXY` remain deliberately capped at runtime corroboration in the governance resolver. Adding T6/T7 metadata must **not** turn a triage label into a confirmed interception or compromise verdict.

---

## Quick reference

| Tier | Question answered |
|---|---|
| T0 | What was noted? |
| T1 | What is configured? |
| T2 | What runtime evidence corroborates it? |
| T3 | Can the behavior/path impact be reproduced? |
| T4 | Who wrote/confirmed the relevant action? |
| T5 | Is the human-governed action backed by verified audit evidence? |
| T6 | Does a controlled change/failure/rollback experiment reproduce the bounded mechanism? |
| T7 | Can a separate verifier validate integrity and reproduce the decision? |

---

## Portfolio positioning

The upgrade changes the model from an evidence-maturity ladder into an **evidence-assurance ladder**. T6/T7 should only be claimed when the required fixture/test evidence exists; documentation alone must never upgrade a case.

## Related documents

- [audit-evidence-model.md](audit-evidence-model.md)
- [proof-vs-observation.md](proof-vs-observation.md)
- [replay-demo.md](replay-demo.md)
- [test-strategy.md](test-strategy.md)
- [evidence_to_action_governance_model.md](evidence_to_action_governance_model.md)
