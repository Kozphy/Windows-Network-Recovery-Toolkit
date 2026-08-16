# Senior Assurance Governance

This upgrade adds a deterministic assurance layer above incident classification and control testing and wires it directly into the existing `RiskDecisionRecord` path.

## Decision chain

```text
Evidence
  -> Risk classification
  -> Control testing
  -> Control exceptions
  -> Remediation ownership / due date
  -> Verification evidence
  -> Residual risk
  -> Human review
  -> Management sign-off (when material)
  -> Assurance conclusion
  -> RiskDecisionRecord / governance report
```

## What changed

The platform already collected evidence, assigned proof tiers, tested controls, rated risk, and gated remediation. The upgraded path now also answers:

1. Are the available facts sufficient to support a conclusion?
2. Which control exceptions remain open, who owns them, and do they materially block closure?
3. Has remediation been independently verified rather than merely reported complete?
4. Is management explicitly accountable for accepting material residual risk?
5. Can the incident actually be closed?

`src/platform_core/governance/senior_assurance.py` contains the deterministic policy engine. `assurance_adapter.py` converts existing incident fixtures and mature-control results into the normalized assurance facts consumed by that engine.

`build_risk_decision_record()` now embeds:

- `assurance_decision`
- `exception_register`

Because the existing risk assessment and governance report already expose the `RiskDecisionRecord`, assurance results flow into the existing reporting path without requiring a separate command.

## Assurance conclusions

- `effective` — evidence is sufficient, review gates are satisfied, controls meet the closure threshold, and no unresolved material exception remains.
- `effective_with_observations` — the environment is broadly supportable, but a non-material exception or governance gate prevents a clean conclusion.
- `ineffective` — critical control failure or unresolved high/critical exception exists.
- `insufficient_evidence` — available evidence cannot support a reliable conclusion; closure is blocked.

## Exception lifecycle

```text
open
  -> in_remediation
  -> pending_validation
  -> closed
```

`risk_accepted` is a separate terminal state for an exception formally accepted by management.

A claimed `closed` exception without validation evidence is automatically downgraded to `pending_validation`. This prevents metadata alone from manufacturing control closure.

Every exception supports:

- control ID
- risk level
- accountable owner
- remediation due date
- remediation plan
- validation evidence IDs
- management acceptance ID

## Material residual risk

High and critical residual risk require explicit `ManagementSignOff`. The sign-off must accept a risk level at least as severe as the actual residual risk. A sign-off that accepts only `medium` risk cannot close a `high` residual-risk decision.

This prevents a common governance failure: treating the presence of an approver name as evidence that the actual residual exposure was accepted.

## Human review and verification

The adapter is conservative:

- policy requiring review does **not** mean review was completed;
- a remediation plan does **not** mean remediation was verified;
- exception status alone does **not** prove validation;
- missing evidence does not silently become a positive assurance conclusion.

Explicit fixture assurance metadata can record completed review, verified remediation, critical control IDs, exception lifecycle details, and management sign-off.

## Safety boundary

This module **does not grant execution authority**. Remediation remains subject to the repository's existing policy gates, preview-only defaults, and human approval mechanisms.

The assurance layer is also **not a regulatory attestation**. It is an internal governance / portfolio decision model that makes assumptions, limitations, accountability, and closure conditions explicit.

## Reviewer behavior demonstrated

```text
Claim
  -> Evidence
  -> Control objective
  -> Test result
  -> Exception
  -> Risk impact
  -> Owner + SLA
  -> Remediation
  -> Independent verification
  -> Residual risk
  -> Management accountability
  -> Assurance conclusion
```

The important change is that the platform no longer stops at "a risk was found." The closure decision itself is now structured, reviewable, reproducible, and attached to the incident decision artifact.