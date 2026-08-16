# Senior Assurance Governance

This upgrade adds a deterministic assurance layer above incident classification and control testing.

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
```

## Why this layer exists

The platform already collects evidence, assigns proof tiers, tests controls, and gates remediation. A senior reviewer, however, must also answer four additional questions:

1. Are the available facts sufficient to support a conclusion?
2. Which control exceptions remain open, who owns them, and do they materially block closure?
3. Has remediation been independently verified rather than merely reported complete?
4. Is management explicitly accountable for accepting material residual risk?

`src/platform_core/governance/senior_assurance.py` encodes those decisions as deterministic policy rather than free-form AI judgment.

## Assurance conclusions

- `effective` — evidence is sufficient, review gates are satisfied, controls meet the closure threshold, and no unresolved material exception remains.
- `effective_with_observations` — the control environment is broadly supportable, but non-material exceptions, incomplete verification, missing human review, low control effectiveness, or missing material-risk sign-off prevent a clean conclusion.
- `ineffective` — critical control failure or unresolved high/critical exception exists.
- `insufficient_evidence` — evidence cannot support a reliable conclusion; closure is always blocked.

## Material residual risk

High and critical residual risk require explicit `ManagementSignOff`. The sign-off must accept a risk level at least as severe as the actual residual risk. A sign-off that accepts only `medium` risk cannot close a `high` residual-risk decision.

This prevents a common governance failure: treating a name in an approval field as proof that the actual residual exposure was accepted.

## Exception lifecycle

```text
open
  -> in_remediation
  -> pending_validation
  -> closed
```

`risk_accepted` is a separate terminal state for an exception formally accepted by management. Open high/critical exceptions block assurance closure.

Every exception supports:

- control ID
- risk level
- accountable owner
- remediation due date
- remediation plan
- validation evidence IDs
- management acceptance ID

## Safety boundary

This module **does not grant execution authority**. Remediation remains subject to the repository's existing policy gates, preview-only defaults, and human approval mechanisms.

The assurance layer is also **not a regulatory attestation**. It is an internal governance / portfolio decision model that makes assumptions, limitations, accountability, and closure conditions explicit.

## Reviewer behavior demonstrated

The resulting workflow is closer to a senior Technology Risk / IT Audit review pattern:

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

The important change is that the platform no longer stops at "a risk was found." It makes the closure decision itself reviewable and reproducible.
