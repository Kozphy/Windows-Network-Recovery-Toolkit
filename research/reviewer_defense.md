# Research-Engineering Reviewer Defense

This document is a self-test for whether the contributor can defend the system rather than merely present generated artifacts.

## Architecture

### Why deterministic evidence rather than an opaque end-to-end model?
The bounded reliability domain benefits from inspectable evidence, reproducible decisions, explicit limitations, and policy separation. A learned model may later assist ranking or explanation, but it should be compared experimentally rather than assumed superior.

### Why separate classification from remediation authorization?
A technically plausible diagnosis does not imply that an action is permitted, safe, timely, or approved. Keeping these stages separate makes unsafe coupling visible and testable.

### Why retain abstention?
Insufficient or contradictory evidence should not be converted into artificial certainty. Abstention is a first-class outcome whose cost and safety benefit should be measured.

## Reliability

### What happens at larger fleet size?
Do not answer with an architectural promise. Report only measured throughput, latency, memory, failure rate, and experimental conditions. Synthetic scale is evidence about computational behavior, not proof of enterprise production reliability.

### What happens on duplicate or reordered evidence?
The desired behavior must be defined as an invariant and covered by deterministic tests before claiming idempotent or order-safe processing.

### What happens when persistence or telemetry fails?
Failure should be explicit rather than silently converted into successful classification or execution. The exact behavior is implementation-specific and must be demonstrated by failure-injection tests.

## Research

### What is the hypothesis?
The principal hypothesis is that proof-aware evidence fusion and abstention can reduce unsafe remediation recommendations relative to simpler baselines on a defined evaluation set.

### What is the baseline?
Use the baselines defined in `research/baselines.md`. Do not compare only against intentionally weak straw-man behavior.

### What would falsify the hypothesis?
Examples include no meaningful reduction in unsafe recommendations, materially worse diagnostic quality at comparable coverage, or an ablation showing that the proposed proof mechanism contributes no measurable benefit.

### What is novel?
Novelty is not established by repository complexity. Any novelty claim requires related-work review and a precise statement of what mechanism, combination, or empirical finding is not already established. Until that work is complete, describe the project as an implementation and evaluation of an evidence-guided decision architecture, not a research breakthrough.

## AI-assisted development

### Did AI write this?
AI assistance may be used, but the relevant question is whether the contributor understands and can defend the artifact. See `research/ai_assisted_engineering_protocol.md`.

### How do you prevent AI-generated confidence from becoming evidence?
Measurements come from executable experiments; claims are tied to artifacts; unknown results remain `TBD`; safety decisions remain deterministic and human-authorized.

## Admission/interview rule

Never memorize these answers verbatim. A strong defense should reconstruct the reasoning from the architecture, tests, measurements, and limitations. If a reviewer changes an assumption, the contributor should be able to reason through the consequence rather than repeat documentation.
