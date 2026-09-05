# Enterprise AI Layer

This package extends the existing decision platform with explicit AI governance primitives: model registration, evaluation, policy gating, human review, runtime monitoring, and auditable decision records.

## Flow

Evidence -> Features/Retrieval -> Model/Agent -> Evaluation -> Confidence -> Policy/Guardrails -> Human Review -> Tool Execution -> Monitoring -> Audit

## Design goals

- Keep AI decisions explainable and reviewable.
- Separate model output from action authorization.
- Fail closed when confidence, policy, or evaluation gates are not satisfied.
- Emit append-only audit events for every decision stage.
- Support deterministic replay using captured inputs, model metadata, and policy versions.
