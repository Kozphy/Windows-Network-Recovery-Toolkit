# AI Governance & Assurance Layer

This layer turns AI-assisted decisions into reviewable control evidence rather than treating model output as an executable instruction.

## Control flow

```text
Evidence / Data
      |
      v
Data lineage + content hash
      |
      v
Model version + Prompt version
      |
      v
AI recommendation / rationale
      |
      v
Risk rating
      |
      v
Control evaluation
      |
      +---- failed --------> BLOCK + evidence
      |
      v
Human approval (high / critical risk)
      |
      +---- denied --------> BLOCK + evidence
      |
      v
Deterministic action
      |
      v
Independent verification
      |
      +---- failed --------> rollback / escalation
      |
      v
Audit evidence package
```

## Evidence retained per AI decision

- decision / use-case identifier
- provider, model, model version, and deployment identifier
- prompt identifier, prompt version, and SHA-256 template hash
- source system and dataset lineage
- input and output hashes
- concise rationale summary
- risk rating
- control results and evidence references
- accountable human approver for high-risk actions
- deterministic action reference
- verification status
- rollback reference
- immutable-style evidence digest for downstream audit logging

## Assurance questions this enables

| Assurance question | Evidence |
|---|---|
| Which AI produced the recommendation? | `ModelVersion` |
| Which prompt/configuration was used? | `PromptVersion.template_hash` |
| What data drove the decision? | `DataLineage` |
| Why was the action considered acceptable? | rationale + `ControlResult` |
| Was an accountable person involved? | `ApprovalRecord` |
| Can the decision be reproduced and reviewed? | hashes + lineage + versions |
| Was the action successful? | `verification_status` |
| Can it be reversed? | `rollback_ref` |

## Big 4 / Technology Risk positioning

The implementation demonstrates separation of duties between AI recommendation and execution, evidence-based control testing, human-in-the-loop approval, traceability, verification, and rollback readiness. These are portfolio-level examples of the concepts used in AI governance, technology risk, internal control, and AI assurance engagements.

The included framework labels are illustrative mappings, not a certification or claim of compliance. Production mappings should be tied to an organization's approved control library and tested evidence requirements.

## Example

```python
from platform_core.ai_governance import AIGovernanceAssuranceService

service = AIGovernanceAssuranceService()
assessment = service.evaluate(record)

if not assessment.allowed:
    raise PermissionError(assessment.reasons)

# Only deterministic, allow-listed execution should occur after this gate.
```
