# Assurance Methodology

This layer upgrades the platform from evidence-backed risk tooling to reviewable assurance engineering. It does **not** provide absolute assurance and must not emit claims such as “guaranteed safe” or “no problems exist.” Conclusions are bounded by scope, criteria, procedures, evidence quality, exceptions, and limitations.

## Decision chain

`Risk -> Control objective -> Criteria -> Procedure -> Evidence -> Sampling -> Exceptions -> Materiality -> Human review -> Conclusion -> Audit trail`

## Minimum control-test contract

Every assurance workpaper should identify:

1. **Risk** — the failure or exposure being addressed.
2. **Control objective** — the state the control is intended to achieve.
3. **Criteria** — the authoritative expected condition or approved baseline.
4. **Scope** — systems, population, period, and exclusions.
5. **Procedure** — inspection, inquiry, observation, reperformance, or automated test steps.
6. **Evidence** — uniquely identified evidence with provenance and limitations.
7. **Sampling** — population, method, sample size, deterministic seed where applicable, and selected items.
8. **Exceptions** — observed deviation, criteria, likelihood, impact, materiality, residual risk, and rationale.
9. **Review** — named human decision for conclusions that require judgment.
10. **Conclusion** — effective, effective with exceptions, ineffective, or inconclusive.

## Evidence sufficiency

Evidence quality is assessed on relevance, reliability, completeness, timeliness, independence, provenance, and explicit limitations. Evidence quantity cannot compensate for fundamentally unreliable evidence.

The existing project evidence tiers remain the provenance/confidence vocabulary; this assurance layer adds the workpaper-level question: *is the evidence sufficient and appropriate for this specific control objective and scope?*

## Reproducible sampling

Random sampling must persist the pseudo-random seed and selected item identifiers. A reviewer must be able to recreate the sample from the same population snapshot. Judgmental sampling must document the selection rationale and must never be described as statistically representative.

## Exception and materiality assessment

Severity alone is not a conclusion. Each exception is evaluated against explicit criteria and records impact, likelihood, materiality, residual risk, and rationale. Potentially material or material exceptions require human review.

## Human review boundary

Automation may collect evidence, execute deterministic procedures, propose exception classifications, and draft a conclusion. Automation must not silently convert uncertainty into assurance. A reviewer may approve, reject, override with rationale, or require more evidence.

## Defensible conclusion language

Preferred form:

> Based on the procedures performed and evidence obtained for the defined scope, the control was assessed as effective / effective with exceptions / ineffective / inconclusive, subject to the documented limitations.

Avoid absolute language such as “100% safe,” “guaranteed,” “fully compliant,” or “no issues exist.”

## Workpaper lifecycle

`prepared -> evidence complete -> tested -> exceptions evaluated -> reviewed -> finalized`

Finalized workpapers should reference immutable or hash-verifiable evidence identifiers and the platform audit trail so another reviewer can trace the conclusion back to source evidence.

## Example mapping: endpoint proxy drift

- Risk: unauthorized or inconsistent proxy configuration can redirect or interrupt traffic.
- Control objective: endpoint proxy configuration is authorized and consistent with policy.
- Criteria: approved WinINET / WinHTTP / policy baseline.
- Procedure: collect snapshots, compare paths, reperform deterministic policy checks, record discrepancies.
- Evidence: registry snapshot, WinHTTP output, policy snapshot, timestamps, custody identifiers.
- Exception: observed state differs from approved baseline.
- Conclusion: never inferred only from anomaly severity; it is bounded by scope, evidence quality, exceptions, and review.
