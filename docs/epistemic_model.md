# Epistemic model: Observation, Inference, and Proof

This platform separates **what was measured** from **what was concluded** and from **what was demonstrated** by a targeted check. Treating these as interchangeable leads to unsafe repairs, audit failures, and false certainty in incident reviews.

## Definitions

### Observation

An **observation** is a recorded fact from a collector, snapshot, or replayed fixture: e.g. a registry value at time *T*, a probe outcome, a parsed log line. Observations can be wrong (stale, incomplete, or mis-sampled) but they are the **only** inputs that directly represent the endpoint at capture time.

- **Not:** a story about intent, attribution, or “why” the failure happened.

### Inference

An **inference** is a machine- or rule-derived hypothesis that explains or classifies observations: layer labels (L3 vs L7), ranked failure scenarios, state transitions, confidence scores. Inferences compress many observations into a **candidate** explanation.

- **Not:** proof of causality, proof of malicious action, or proof that a specific process wrote a registry value.
- **Confidence** in this codebase is an **ordinal ranking weight** for ordering hypotheses and driving UX emphasis — **not** a calibrated probability unless a separate calibration pipeline is documented and versioned.

### Proof

**Proof** (in the platform sense) comes from **structured, replayable checks** with explicit outcomes such as CONFIRMED / REJECTED / INCONCLUSIVE — for example proxy bypass contrast, DNS contrast, or registry-write telemetry when available. Proof **strengthens or limits** what language and policy may claim; it does **not**, by itself, authorize mutation (policy is separate).

## Relationships (what does *not* follow)

| If you have | You may **not** automatically claim |
|-------------|-------------------------------------|
| Observations | Root cause, attacker identity, or safe to repair |
| High-confidence inference | Certainty, or permission to execute destructive remediation |
| Listener / process correlation | Registry writer identity (without appropriate write telemetry) |
| Proof of a network path issue | The whole system is secure or that no other fault exists |

## Policy is orthogonal

Even with CONFIRMED proof for a narrow scenario, **policy** still gates **ALLOW / PREVIEW / BLOCK**, confirmations, RBAC, and residual risk messaging. **Policy ALLOW ≠ no risk.**

## Operational habit

When reading any diagnosis or dashboard:

1. Start from **observed signals** (raw or normalized IDs).
2. Read **hypotheses** as ranked candidates with limitations.
3. Inspect **proof status** before treating language as strong.
4. Read **policy** and **required_confirmation** before any execute path.

Replay from stored observations must reproduce the same reasoning chain **without live re-probing** the machine; if replay required new sockets or subprocess probes, the audit envelope would not be sufficient for offline review.

## See also

- Root `README.md` — safety table and “Observation vs Inference vs Proof”
- `docs/event_state_reasoning_platform.md` — event/state pipeline
- `platform_core/reasoning_engine.py` — deterministic reasoning without host I/O
- `platform_core/reasoning_audit.py` — replay from audit records
