# Research Discussion Framework

Use this document after the frozen evaluation run. Do not write the conclusion before metrics and error analysis are complete.

## If H1/H2 are supported

Explain the observed effect size, confidence interval, which classes improved, and which evidence families drove the gain. Avoid saying the system is generally superior outside the declared dataset.

## If results are null

A null result means the full classifier did not demonstrate a clear advantage under this protocol. Discuss whether the likely explanation is redundant evidence, insufficient sample size, label ambiguity, or genuinely equivalent performance. Do not change the primary metric post hoc.

## If a baseline wins

Treat this as informative. A simpler baseline may be preferable when complexity does not buy measurable reliability, safety, or explainability. Identify which components add complexity without demonstrated value.

## Error-centered interpretation

Aggregate metrics must be accompanied by case-level discussion of:

- false positives that could trigger unnecessary operator action
- false negatives in critical drift classes
- low-proof-tier outputs
- conflicting evidence cases
- ambiguous labels

## Research contribution

The strongest defensible contribution of this repository is not “perfect diagnosis.” It is a testable governance architecture that connects deterministic endpoint evidence, explicit uncertainty/limitations, control testing, policy gates, auditability, and reproducible evaluation.

## Required conclusion structure

1. question asked
2. protocol and dataset scope
3. primary result with uncertainty
4. baseline comparison
5. ablation findings
6. dominant error modes
7. threats to validity
8. operational implication
9. non-claims
10. next falsifiable experiment
