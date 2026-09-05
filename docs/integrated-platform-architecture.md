# Integrated Assurance and Reliability Platform

## Purpose

This repository is positioned as a deterministic decision platform that combines endpoint diagnostics, reliability engineering, security governance, AI assurance, audit-ready evidence, and continuous prompt-free monitoring.

## End-to-end flow

```text
incident, timer, startup trigger, or signal
  -> continuous read-only agent
  -> deterministic observation
  -> normalized evidence
  -> policy decision
  -> bounded harness
  -> optional AI explanation
  -> approval gate
  -> remediation adapter
  -> verification and replay
  -> audit evidence and analytics
```

## Continuous operation

The continuous agent runs without user prompts and periodically executes only checks listed in a trusted local configuration. It fingerprints results, detects state changes, persists audit JSONL, and writes escalation records. It does not perform remediation.

On Windows, the reference installer creates a restartable at-startup Scheduled Task. This is more accurate than registering plain Python directly as a native Windows Service. A signed service wrapper remains a later packaging step.

## Control boundaries

- Observation is automatic and read-only.
- Command execution uses an explicit configuration list and `shell=False`.
- Unknown check types produce error evidence rather than arbitrary execution.
- State-change alerting reduces notification storms.
- Privileged remediation requires deterministic policy authorization and human approval.
- AI output is explanation-only and cannot override policy.
- Every decision and verification result is retained as audit evidence.

## Platform components

| Layer | Responsibility |
|---|---|
| Continuous agent | Prompt-free observation, change detection, evidence and escalation |
| Endpoint diagnostics | Collect deterministic host and network observations |
| Evidence normalization | Produce stable schemas and evidence tiers |
| OPA/Rego policy | Apply default-deny action authorization |
| Bounded harness | Verify, score, stop and escalate |
| AI assurance layer | Provide cited explanations under release gates |
| OpenTelemetry | Trace diagnostic and decision flows |
| Prometheus/Grafana | Monitor reliability, policy and review metrics |
| Kubernetes/Compose | Supply reference execution environments |
| GitHub Actions | Validate harness, agent, security and supply-chain controls |
| Audit analytics | Export JSONL and governance evidence for reporting |

## Design rules

1. Deterministic checks remain authoritative.
2. Continuous observation stays read-only.
3. AI outputs are advisory and must include evidence references.
4. High-impact actions require explicit approval.
5. Every loop has an iteration, time and scope limit.
6. Policy failures default to deny.
7. Telemetry must not contain secrets or raw sensitive payloads.
8. Deployment artifacts must be pinned before production use.

## Current implementation status

Implemented as merge-safe components:

- bounded harness and sample tasks;
- read-only continuous monitoring loop;
- state fingerprints and append-only JSONL evidence;
- Windows startup-task installer;
- continuous-agent unit tests and CI validation;
- Rego reference policy;
- OpenTelemetry and Prometheus reference configuration;
- CodeQL, dependency audit and SBOM workflows;
- Kubernetes and Compose reference deployments.

Still requiring runtime integration:

- real OPA calls from application and agent flows;
- application-level OpenTelemetry instrumentation;
- approved alert delivery channel;
- real endpoint classifiers and replay fixtures;
- signed, digest-pinned production packaging.

## Portfolio narrative

The architecture demonstrates that autonomous operation does not require uncontrolled autonomy. The system continuously observes and verifies, while policy, approval, replay and audit controls constrain higher-risk actions.
