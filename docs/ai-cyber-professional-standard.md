# AI & Cybersecurity Professional Standard

This document turns the repository's portfolio claims into a measurable engineering standard. It is designed for review by Technology Risk, Cyber Risk, Platform/SRE, AI Governance, and internal-audit interviewers.

## Positioning

The platform demonstrates **AI-assisted technology-risk engineering**, not autonomous cyber defence. Deterministic evidence and policy logic remain authoritative. AI may summarize, explain, prioritize, or draft recommendations, but it cannot authorize or execute remediation.

## Capability matrix

| Domain | Required evidence | Repository target | Acceptance criterion |
| --- | --- | --- | --- |
| Secure engineering | Static analysis, dependency review, secrets hygiene | GitHub security CI | Every pull request receives automated security checks; high-confidence findings are triaged before merge |
| Threat modeling | Assets, trust boundaries, abuse cases, mitigations | `docs/threat-model.md` | Every new execution path documents abuse cases and control ownership |
| Responsible AI | Human approval, non-claims, limitations, traceability | README, policy gates, decision records | AI output cannot mutate state; explanations identify evidence and limitations |
| Model/evaluator quality | Repeatable test set, error taxonomy, regression thresholds | deterministic fixtures and replay | Evaluation results are reproducible from versioned inputs and configuration |
| Data governance | minimization, redaction, retention, lineage | audit JSONL and release checks | No secrets or raw production identifiers enter committed fixtures |
| Identity and access | least privilege, role boundaries, explicit authorization | API/operator controls | Privileged operations deny by default and emit auditable decisions |
| Detection integrity | evidence/inference separation | proof tiers T0–T5 | No compromise or malware verdict is produced from heuristic evidence alone |
| Remediation safety | preview, approval, rollback, idempotency | policy-gated workflow | Risky changes require typed confirmation and generate before/after evidence |
| Auditability | immutable event sequence, actor, reason, hashes | hash-chained JSONL | Tampering is detected and replay reconstructs the decision path |
| Operational resilience | health checks, deterministic replay, failure modes | API, fixtures, runbooks | Core read-only diagnostics remain usable when optional AI or database services fail |

## AI control requirements

### 1. Purpose limitation

Each AI-assisted function must declare:

- intended user and decision;
- permitted inputs and outputs;
- prohibited actions;
- authoritative non-AI fallback;
- known limitations and escalation path.

### 2. Evidence grounding

AI explanations must reference structured evidence identifiers or fields. The system must distinguish:

1. observation;
2. hypothesis;
3. proof tier;
4. policy result;
5. human approval;
6. execution outcome.

Generated text must never collapse these stages into a single unsupported conclusion.

### 3. Human authorization

AI output is advisory. The following remain human-controlled:

- enabling live execution;
- approving registry or system changes;
- accepting risk exceptions;
- assigning incident severity above the evidence-supported ceiling;
- publishing external or committee-facing conclusions.

### 4. Evaluation

Every AI-assisted capability should have a versioned evaluation pack containing:

- representative normal, ambiguous, and adversarial cases;
- expected evidence citations;
- prohibited claims;
- refusal/escalation cases;
- regression thresholds;
- reviewer sign-off for material changes.

Recommended metrics include grounded-claim rate, prohibited-claim rate, evidence coverage, escalation precision, and deterministic fallback success.

### 5. Prompt and model change management

Prompt, model, retrieval, tool, or policy changes are treated as controlled changes. Pull requests should record:

- reason for change;
- evaluation delta;
- new failure modes;
- rollback path;
- residual risk owner.

## Cybersecurity control requirements

### Secure-by-default invariants

- no autonomous execution;
- no secret collection;
- no cloud upload by default;
- no firewall reset, adapter disable, process termination, or registry mutation outside explicit allowlisted flows;
- no unbounded shell invocation;
- no use of untrusted text as executable instructions;
- no security verdict beyond available proof.

### Pull-request security gate

A production-shaped pull request should pass:

```text
unit and safety tests
→ static analysis
→ dependency vulnerability scan
→ dependency change review
→ secrets/public-release hygiene
→ threat-model impact review
→ human approval
```

Automated findings are evidence for review, not automatic proof of exploitability. Triage should record reachability, prerequisites, affected assets, compensating controls, and disposition.

## Recruiter-facing proficiency levels

| Level | Demonstrated behavior |
| --- | --- |
| Foundation | Writes safe scripts, tests basic cases, explains threats and limitations |
| Associate | Implements policy gates, CI checks, audit records, deterministic evaluation, and least-privilege controls |
| Professional | Designs trust boundaries, abuse-case tests, incident workflows, AI evaluation criteria, and control evidence for multiple stakeholders |
| Senior/Lead | Owns enterprise architecture, production incident response, security operations, calibrated model-risk governance, and cross-team risk acceptance |

This repository targets the **Associate-to-Professional** band. It should not be presented as proof of senior offensive-security, SOC leadership, or production ML-research experience.

## Definition of done for new features

A material feature is complete only when it includes:

- tests for intended and prohibited behavior;
- explicit limitations and non-claims;
- threat-model and privacy impact assessment;
- safe default and failure mode;
- audit event schema and replay behavior;
- dependency/security scan results;
- operator documentation and rollback guidance;
- evidence that AI is not in the authorization path.

## Interview statement

> I built a deterministic technology-risk platform that uses AI only for bounded explanation. Evidence collection, proof tiers, policy decisions, approvals, execution, and audit replay remain separated and testable. I added secure-development gates, threat modeling, dependency and static analysis, and measurable responsible-AI controls so the project demonstrates Associate-to-Professional Technology Risk and AI Governance capability without overstating it as an EDR or autonomous security product.
