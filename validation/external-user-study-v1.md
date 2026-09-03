# External User Validation Protocol v1

## Status

**Protocol ready; no external validation result is claimed yet.**

This protocol is designed for enterprise endpoint engineers, support engineers, SREs, security analysts, or other external practitioners who did not author the classifier or benchmark fixtures. Participation must be voluntary, and submitted evidence must be sanitized and lawful to share.

## Objective

Test whether the evidence-tiered report improves diagnosis quality, decision traceability, and time-to-safe-action relative to an external participant's normal diagnostic workflow.

## Minimum evidence threshold

A first external report may be published after all of the following are available:

- at least 5 external participants from at least 2 organizations or independent teams;
- at least 20 independently supplied or independently labeled scenarios;
- participant role and experience-band metadata without personal identifiers;
- predeclared expected labels or adjudication by two reviewers;
- raw, de-identified task records; and
- explicit disclosure of recruitment, exclusions, conflicts, and missing data.

These thresholds support a pilot study only. They do not establish population-level enterprise effectiveness.

## Study design

Use a counterbalanced within-participant design where practical:

1. Assign each participant a random participant code.
2. Randomly divide scenarios into two balanced sets.
3. Diagnose one set with the participant's normal workflow.
4. Diagnose the other set with the evidence-tiered report available.
5. Reverse the ordering for alternating participants to reduce learning effects.
6. Do not reveal expected labels until both conditions are complete.
7. Record exclusions before computing aggregate metrics.

If participants contribute their own incidents, remove hostnames, usernames, IP addresses, domains, tenant identifiers, process arguments, and other sensitive values before repository submission. Do not collect production credentials, tokens, packet payloads, or personal data.

## Primary outcomes

- diagnosis correctness against the predeclared or adjudicated label;
- macro precision, recall, F1, and false-positive rate;
- unsupported-conclusion rate;
- unsafe-change-proposal rate;
- time-to-diagnosis in seconds; and
- time-to-safe-next-action in seconds.

## Secondary outcomes

- number of diagnostic steps;
- number of setting changes attempted;
- unnecessary change/reversal count;
- evidence traceability rating (1–5);
- report clarity rating (1–5); and
- decision confidence before label reveal (1–5).

## Task procedure

For each scenario:

1. Start the timer when the participant receives the case.
2. Record tools and evidence inspected, without capturing sensitive content.
3. Stop the diagnosis timer when a final incident class is selected.
4. Record the proposed next action and whether approval is required.
5. Stop the safe-action timer when the participant identifies a policy-compatible next step.
6. Collect the three 1–5 ratings.
7. Reveal neither oracle nor other-condition output until the session ends.

## Adjudication

Two reviewers should independently label externally supplied cases using the published taxonomy. Resolve disagreements through a recorded consensus decision. Preserve the original labels, reviewer codes, disagreement flag, and final adjudicated label. Reviewers should not see system predictions before adjudication.

## Safety rules

- Use replay, lab, or already-resolved incidents; do not induce failures on production endpoints.
- Keep remediation preview-only unless an organization's normal change control explicitly authorizes a lab action.
- Never weaken security controls, disable endpoint protection, or bypass organizational policy for the study.
- Stop a task if sensitive data appears or the participant is uncertain about authorization.

## Analysis plan

Compute task-level paired differences between normal workflow and evidence-tiered assistance. Report exact counts and participant/scenario counts with every percentage. For time outcomes, report median and interquartile range because pilot samples may be skewed. If inferential tests are used, predeclare the test and assumptions before examining condition aggregates. Publish all exclusions and missing observations.

Subgroup summaries must not identify a participant or organization. Do not report organization-level results when fewer than three participants would make re-identification plausible.

## Claim gate

External-validation language is allowed only when the de-identified response table, provenance note, adjudication record, analysis script, and generated report are committed together. Until then, use exactly:

> External validation protocol published; external validation not yet completed.

## Data-entry template

Use `validation/external-user-study-v1-template.csv`. One row represents one participant-scenario-condition observation. Do not replace participant codes with names or email addresses.

