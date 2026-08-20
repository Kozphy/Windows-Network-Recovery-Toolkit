# Cambridge / Oxford Independent Research Track

## Research thesis

**When is operational evidence sufficient to justify automated intervention under uncertainty?**

Windows network configuration drift is the experimental domain, not the ultimate claim. The broader research object is evidence-based decision making for systems that must choose among intervention, abstention, and human escalation when observations are incomplete, noisy, or contradictory.

## Formal decision framing

Let:

- `E` denote observed evidence;
- `Y` denote the latent true system state;
- `A = {intervene, abstain, escalate}` denote available actions;
- `L(a, y)` denote the loss associated with action `a` when the true state is `y`.

The ideal decision minimizes conditional expected loss:

`a* = argmin_a E[L(a, Y) | E]`

The central operational assumption is asymmetric loss: an incorrect remediation may be substantially more costly than abstention or human review. Therefore classification accuracy alone is not an adequate objective.

This formulation is a research hypothesis and decision model, not evidence that the current implementation estimates calibrated probabilities or optimal losses.

## Core questions

### RQ1 — Evidence sufficiency
Under what combinations of evidence is intervention justified rather than abstention or escalation?

### RQ2 — Contradiction
How does contradictory cross-source evidence affect decision reliability and false-remediation risk?

### RQ3 — Distribution shift
How robust are evidence-fusion rules when scenario distributions, missingness patterns, environments, or failure mechanisms differ from development conditions?

### RQ4 — Asymmetric cost
How do optimal decision thresholds change as the relative cost of false remediation, missed remediation, abstention, and escalation changes?

### RQ5 — Generalization boundary
Which findings are specific to Windows proxy/network drift, and which mechanisms plausibly transfer to other operational-control domains?

## What would falsify the thesis?

Evidence against the proposed direction includes:

1. simple single-source baselines matching or exceeding evidence fusion on held-out scenarios;
2. evidence fusion increasing false-remediation risk under contradiction or missingness;
3. abstention providing no safety benefit at comparable operational coverage;
4. apparent gains disappearing under distribution shift or independent reproduction;
5. conclusions depending primarily on benchmark construction artifacts.

Negative results must be retained and discussed.

## Required contribution ladder

### C0 — Engineering artifact
Existing deterministic platform, evidence collection, controls, policy gates, audit trail, and replay.

### C1 — Empirical benchmark
Versioned held-out benchmark, baselines, reproducible metrics, uncertainty intervals.

### C2 — Scientific explanation
Ablations and failure analysis explaining *why* results change.

### C3 — Robustness
Missing evidence, contradictory evidence, temporal drift, environment variation, and out-of-distribution scenarios.

### C4 — Literature-grounded novelty
A precise claim that is not merely implementation novelty and is positioned against external peer-reviewed work.

### C5 — Independent research artifact
Paper-quality argument with explicit assumptions, limitations, reproducible artifacts, and results capable of being challenged by another researcher.

## Oxbridge-quality test

The project is not ready merely because it contains many tests or production-shaped components. A reviewer should be able to answer:

- What is the research gap?
- Why is the question intellectually important beyond this codebase?
- What assumptions make the argument work?
- What evidence would overturn the conclusion?
- Which external methods are credible comparators?
- Is the evaluation independent of method development?
- Are uncertainty and negative results visible?
- Does the contribution survive reasonable distribution shift?
- Can another researcher reproduce the result?

## Required next artifacts

1. `LITERATURE_REVIEW.md` — peer-reviewed literature map and defensible gap.
2. `THEORETICAL_FRAMEWORK.md` — assumptions, decision loss, abstention and testable propositions.
3. `reproduction/` — one external paper reproduced before extending it.
4. `robustness/PROTOCOL.md` — preregistered shift and contradiction experiments.
5. executable benchmark/baseline runner and raw-result retention.
6. 6–8 page research paper plus appendix.

## Claim discipline

Until experiments exist, use future-tense language: *we propose*, *we will test*, *the benchmark is designed to evaluate*. Do not write *our method improves*, *reduces*, *generalizes*, or *is safer* without measured evidence supporting the exact claim.

## End state

The desired portfolio story is not "a large Windows repair project." It is:

> A reproducible study of evidence sufficiency, abstention, and asymmetric-cost intervention under operational uncertainty, evaluated through Windows configuration drift as a controlled systems domain.

That framing remains provisional until the literature review establishes a genuine research gap.