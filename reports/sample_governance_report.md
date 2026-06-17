# Technology Risk & Control Governance Report

**Case ID:** CASE_1_DEAD_WININET_PROXY
**Schema:** technology_risk_decision.v1

## Executive Summary

Technology risk assessment for governance support — not antivirus, EDR, or XDR. Observation ≠ proof; correlation ≠ causation.

Inherent medium / residual medium for DEAD_PROXY_CONFIG (proof: supported).

## Business Objective

- **Maintain reliable and secure browser/network access** — Ensure corporate endpoints can reach business web applications without misconfigured proxy state or unaudited configuration drift.
- Owner: IT Operations / Endpoint Engineering

## Asset & Threat

- **Asset:** Windows endpoint WinINET proxy settings (endpoint_configuration)
- **Threat:** Dead localhost proxy breaks browser traffic — WinINET references localhost proxy port with no active listener

## Findings

- **Dead Proxy Config** (DEAD_PROXY_CONFIG) — tier: proof, confidence: 0.92
- **WinINET and WinHTTP proxy paths diverge** (WININET_WINHTTP_MISMATCH) — tier: proof, confidence: 0.92
- **Control test failed: Proxy configuration monitoring and drift detection** (CT_PROXY_DRIFT) — tier: observation, confidence: 0.5

## Risk Rating

| Inherent | Residual | Likelihood | Impact | Control effectiveness |
|----------|----------|------------|--------|----------------------|
| medium | medium | medium | medium | 0.4 |

## Control Test Results

- **Proxy configuration monitoring and drift detection**: FAIL — DEAD_PROXY_CONFIG with signals WININET_WINHTTP_MISMATCH, LOCALHOST_PROXY, DEAD_LOCALHOST_PORT
- **Structured proof envelope**: PASS — Proof conclusion: supported
- **Registry writer attribution**: NOT_TESTED — Writer attribution not in scope
- **Policy-gated remediation**: PASS — PREVIEW_ONLY
- **Append-only audit trail**: NOT_TESTED — Audit verification not run

## Governance Decision

- Outcome: **PREVIEW_ONLY**
- Dry-run: **True**
- Recommended action: DISABLE_WININET_PROXY
- Owner: IT Operations / IT Governance

## Limitations

- Confidence is ordinal (0–1), not a statistical probability.
- Correlation and proof do not equal final causation without strong telemetry.
- This rating supports governance discussion; it is not a regulatory attestation.
