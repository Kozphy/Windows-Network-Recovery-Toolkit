# Theoretical Framework: Intervention Under Uncertain Evidence

## 1. Scope

This document defines a falsifiable decision framework for the research track. It does **not** claim that the current toolkit implements Bayesian inference, calibrated uncertainty, or optimal decision theory. Those are candidate extensions to be evaluated empirically.

## 2. Decision problem

An operational system observes evidence `E` about an unknown state `Y` and chooses an action `a` from:

- `I`: intervene/remediate;
- `A`: abstain and collect more evidence;
- `H`: escalate to human review.

A rationalized decision rule selects the action with minimum expected loss:

`a*(E) = argmin_a Σ_y L(a,y) P(y|E)`

The empirical project must not treat `P(y|E)` as calibrated unless calibration is measured.

## 3. Asymmetric loss

A starting hypothesis is that losses are asymmetric:

`L(false intervention) > L(abstention)`

in safety-sensitive configurations. This is not universal. The relative costs should be treated as scenario parameters and evaluated through sensitivity analysis rather than fixed as an unquestioned constant.

Candidate loss components include:

- service disruption caused by incorrect remediation;
- operational cost of unnecessary human review;
- cost of delayed recovery after abstention;
- cost of failing to remediate a persistent fault;
- governance/audit cost of acting with insufficient evidence.

## 4. Evidence representation

Let evidence be grouped into families:

`E = {E_registry, E_wininet, E_winhttp, E_connectivity, E_tls, E_temporal}`

Evidence may be:

- observed and consistent;
- observed and contradictory;
- missing;
- stale;
- transient;
- potentially distribution-shifted relative to development data.

The framework should distinguish **absence of evidence** from **evidence of absence**.

## 5. Abstention

A classifier that always emits a label may be operationally inferior to one that refuses to act under insufficient evidence. Define coverage as the fraction of cases on which an automated intervention decision is made.

Evaluation should therefore examine a risk–coverage relationship rather than only classification accuracy. A useful system may reduce intervention coverage while sharply reducing unsafe decisions.

### Proposition P1
As the evidence-sufficiency threshold increases, automated intervention coverage should weakly decrease.

### Hypothesis H-P1
Within a nontrivial threshold region, false-remediation risk will decrease faster than useful-remediation coverage, producing a favorable safety/coverage trade-off.

This hypothesis can fail and must be tested.

## 6. Contradictory evidence

Cross-source disagreement is itself information. A naive fusion rule may become overconfident when multiple sources are correlated or derived from the same underlying state.

### Hypothesis H-P2
Explicit contradiction detection plus abstention will reduce false remediation relative to a forced-classification fusion rule on contradiction-focused held-out cases.

## 7. Distribution shift

Let development scenarios follow distribution `P_dev(E,Y)` and deployment-like stress scenarios follow `P_shift(E,Y)`.

Potential shifts include:

- different class prevalence;
- increased evidence missingness;
- different Windows/environment configuration;
- novel combinations of otherwise familiar evidence;
- changed transient/persistent failure ratios;
- measurement noise.

### Hypothesis H-P3
Performance and calibration measured only on `P_dev` will overstate decision reliability under at least one prespecified shift family.

The purpose of this hypothesis is to challenge the system, not to manufacture robustness claims.

## 8. Sensitivity to decision costs

Instead of publishing a single arbitrary loss matrix, evaluate a family of plausible cost ratios.

For example, vary:

`C_false_intervention / C_human_review`

and

`C_missed_persistent_fault / C_abstention`

over preregistered ranges. Plot which action policy is preferred as assumptions change.

A conclusion that reverses under small cost changes should be reported as fragile.

## 9. Calibration

If probabilistic confidence is introduced, ranking confidence must not be described as probability. Candidate calibration evaluation includes reliability diagrams, Brier score, expected calibration error, and calibration under shift. Metric choice must be justified before final evaluation.

## 10. Causal restraint

Ablation can demonstrate dependence of system performance on a component under the experiment; it does not automatically establish a causal mechanism in real deployments. Language should distinguish engineering intervention experiments from broad causal claims.

## 11. Connection to controls and governance

The governance contribution is a decision-accountability layer:

`evidence -> uncertainty -> decision rule -> action/abstention -> audit record -> outcome`

This permits analysis of not only whether a prediction was correct, but whether the available evidence justified the action under declared assumptions.

## 12. Falsification checklist

Before interpreting results, ask:

1. Did a simpler baseline perform equally well?
2. Did threshold tuning leak information from the held-out set?
3. Are evidence sources conditionally dependent in a way the model ignores?
4. Does the result survive missingness and contradiction?
5. Does it survive distribution shift?
6. Is the conclusion sensitive to the chosen loss matrix?
7. Are confidence values actually calibrated?
8. Could benchmark labeling or construction explain the apparent gain?

## 13. Boundary of contribution

Even successful experiments in this repository would initially support claims about the defined Windows network/configuration benchmark. Generalization to autonomous systems, cybersecurity, medicine, finance, or other high-stakes domains would require separate evidence and must not be implied.