# Integrated Assurance and Reliability Platform

## Purpose

This repository is positioned as a deterministic decision platform that combines endpoint diagnostics, reliability engineering, security governance, AI assurance, and audit-ready evidence.

## Control flow

```text
Signal or incident
  -> deterministic observation
  -> normalized evidence
  -> policy decision (OPA-compatible)
  -> bounded harness loop
  -> optional AI explanation
  -> human approval gate
  -> remediation adapter
  -> verification and replay
  -> immutable audit output
```

## Technology layers

| Layer | Primary technology | Repository value |
|---|---|---|
| Execution | Python, FastAPI, bounded harness | Repeatable and testable decisions |
| Policy | Open Policy Agent / Rego contract | Governance separated from application code |
| Telemetry | OpenTelemetry | Vendor-neutral traces, metrics and logs |
| Monitoring | Prometheus and Grafana contract | SLOs, alerting and operational dashboards |
| Delivery | GitHub Actions; Harness-compatible steps | Reproducible CI and controlled promotion |
| Runtime | Docker and Kubernetes | Portable, isolated deployment |
| Supply chain | SBOM, Trivy, CodeQL, artifact signing plan | Verifiable build provenance |
| AI assurance | Evaluation policy and human review | AI remains explanatory and bounded |
| Analytics | JSONL evidence and Power BI export | Audit and management reporting |

## Design rules

1. Deterministic checks remain authoritative.
2. AI outputs are advisory and must include evidence references.
3. High-impact actions require explicit approval.
4. Every loop has an iteration, time and scope limit.
5. Policy failures default to deny.
6. Telemetry must not contain secrets or raw sensitive payloads.
7. Deployment artifacts must be pinned before production use.

## Portfolio narrative

The platform demonstrates the ability to connect engineering and governance rather than treating them as separate concerns:

- SRE: service objectives, replay safety, failure recovery and observability.
- Technology Risk: controls, evidence, exceptions and approval boundaries.
- Cybersecurity Governance: policy-as-code and supply-chain checks.
- AI Engineering: structured evaluation, controlled orchestration and human review.
- Audit Analytics: machine-readable evidence suitable for dashboards and testing.
