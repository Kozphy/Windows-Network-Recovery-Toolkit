# Failure Taxonomy

Use this taxonomy during error analysis and incident review.

| Category | Meaning | Example investigation |
|---|---|---|
| False positive | System predicts elevated risk without the defined outcome | Threshold, noisy feature, transient configuration |
| False negative | Defined outcome occurs despite low predicted risk | Missing signal, unseen environment, stale evidence |
| Data-quality failure | Input is incomplete, invalid, duplicated or stale | Collector/schema validation |
| Label failure | Ground truth is ambiguous, delayed or incorrect | Label adjudication and observation window |
| Feature failure | Feature derivation does not represent intended condition | Transformation/control implementation |
| Distribution drift | Input population differs materially from training evidence | Temporal/environment comparison |
| Model failure | Model behavior is unstable or poorly calibrated | Calibration, subgroup and confidence analysis |
| Policy failure | Valid evidence is mapped to an inappropriate governance action | Threshold/policy review |
| Human-decision failure | Review/approval does not follow intended control | Approval and audit trail |
| Remediation failure | Approved action does not correct the condition | Post-action verification |
| Verification failure | Outcome cannot be reliably confirmed | Evidence collection and test design |

## Required record for analyzed failures

Capture an anonymized case identifier, model/version, dataset/feature version, prediction, actual label/outcome, category, suspected cause, evidence, corrective action and whether the case implies a model, policy, collector or documentation change.