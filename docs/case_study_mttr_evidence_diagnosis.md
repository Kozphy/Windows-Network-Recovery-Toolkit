# Reducing Windows Endpoint Network Incident MTTR Through Evidence-Based Diagnosis

## Executive summary

This case study describes how an evidence-based endpoint reliability decision platform reduces mean time to resolution (MTTR) for Windows proxy and browser-path failures while improving auditability and remediation safety.

## Problem

Endpoints can exhibit `ERR_PROXY_CONNECTION_FAILED` while ping and DNS still succeed. Operators often reset network stacks blindly, increasing risk and repeat incidents.

## Approach

Correlate registry, process, network, browser, and proof signals into:

1. Incident timeline
2. Risk-classified decision
3. Policy-gated remediation preview
4. Audit-ready report

## Business KPIs

| KPI | Target impact |
|-----|----------------|
| MTTR reduction | Faster triage via timeline + ranked hypothesis |
| False positive reduction | Evidence tiers block correlation-only remediation |
| Auditability improvement | Append-only JSONL + replay |
| Remediation safety | dry-run default, typed confirmation |
| Evidence completeness | Multi-source collectors + proof runner |
| Repeatable workflow | Fixture replay on non-Windows CI |

## Portfolio explanation

> I built an endpoint reliability decision platform that diagnoses Windows proxy-related network failures by correlating registry, process, network, browser, and proof signals. The system produces an incident timeline, classifies risk, recommends policy-gated remediation, and exports an audit-ready report.

## Sample finding

Based on collected evidence, the endpoint exhibited WinINET proxy drift: browser path failed through a local loopback proxy while direct path succeeded. Recommended action: disable WinINET proxy only after explicit confirmation, with rollback preparation and audit logging.
