# Evidence-to-Decision Lifecycle

This repository already separates observation, proof, policy, approval, execution, audit, and replay. This document makes the reasoning lifecycle explicit and machine-readable.

## Canonical mental model

```text
Words / Signals
  -> Observation
  -> Claim / Hypothesis
  -> Evidence
  -> Verification
  -> Uncertainty
  -> Knowledge
  -> Decision
  -> Action
  -> Outcome
  -> Feedback / Replay
```

The platform must not jump directly from observation to action.

## First-class artifacts

Implemented in `src/platform_core/governance/evidence_decision_lifecycle.py`:

- `Claim` — falsifiable statement derived from observations.
- `VerificationResult` — explicit record of checks, supporting/contradicting evidence, reproducibility, and limitations.
- `UncertaintyAssessment` — separates ordinal confidence from calibrated probability and records missing evidence and alternative hypotheses.
- `KnowledgeRecord` — bounded, verified statement that can be considered by downstream decision logic.
- `EvidenceDecisionLifecycle` — envelope connecting the above artifacts to the existing `RiskDecisionRecord` decision identifier and future outcome/feedback records.

## Relationship to existing architecture

Existing flow:

```text
Observation -> Hypothesis -> Proof -> Policy -> Stakeholder -> Timing
  -> Preview -> Approval -> Execution -> Audit -> Replay
```

Extended reasoning model:

```text
Observation
  -> Claim
  -> Evidence / Proof
  -> Verification
  -> Uncertainty
  -> Knowledge
  -> RiskDecisionRecord
  -> Policy
  -> Preview / Approval / Execution
  -> Audit
  -> Outcome
  -> Feedback / Replay
```

This is additive. `RiskDecisionRecord` remains the formal technology-risk decision artifact.

## Safety invariants

1. Observation is not proof.
2. Repetition is not independent evidence.
3. Correlation is not causation.
4. Confidence is not certainty.
5. An ordinal confidence score is not a calibrated probability.
6. Classification is not accusation.
7. Verified knowledge does not automatically grant execution authority.
8. Policy permission is not a safety guarantee.
9. Low proof tiers must remain inconclusive or explicitly limited.
10. Decisions must remain replayable from version-pinned evidence and logic.

## Adapter

`lifecycle_from_risk_decision(record)` converts an existing `RiskDecisionRecord` into the explicit lifecycle without changing existing decision behavior.

Current conservative mapping:

| Proof tier | Verification | Knowledge decision-use |
|---|---|---|
| T0-T1 | inconclusive | false |
| T2 | partially verified | true, with limitations |
| T3+ | verified | true, with limitations |

This mapping is intentionally conservative and should evolve only with documented validation evidence.

## Next upgrades

Recommended follow-on work:

- persist lifecycle artifacts alongside audit JSONL;
- add contradictory-evidence handling to classifiers;
- add explicit alternative-hypothesis generation rules;
- add outcome records and measurable decision success criteria;
- connect replay outcomes back into uncertainty calibration;
- expose lifecycle artifacts through `/trisk/*` APIs;
- add Power BI facts for claims, verification outcomes, and decision feedback;
- add calibration tests before interpreting confidence values probabilistically.

## Interview framing

> The platform does not treat statements or classifications as truth. It turns observations into falsifiable claims, binds claims to evidence, verifies them, makes uncertainty explicit, derives bounded knowledge, and only then permits governed human decisions and policy-gated action.
