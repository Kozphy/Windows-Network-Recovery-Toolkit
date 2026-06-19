# ADR: Portfolio Positioning — Evidence Pipeline vs Repair Script

**Status:** Accepted  
**Date:** 2026-06-12

## Context

Windows proxy failures are often fixed with ad-hoc PowerShell that mutates registry keys without audit trails, proof tiers, or control testing. Interviewers and auditors cannot distinguish **observation** from **proof** or **policy** from **automation**.

## Decision

Position this repository as a **Technology Risk & Control Analytics Platform**:

- Read-only evidence collection by default  
- Deterministic state machine for proxy transitions  
- Control tests and governance reports for risk committees  
- Remediation limited to **preview + typed confirmation**  

Do **not** position as antivirus, EDR, or autonomous recovery agent.

## Alternatives considered

| Alternative | Rejected because |
|-------------|------------------|
| “Network fix script” repo | No audit, no controls, unsafe at scale |
| Full EDR product | Scope creep; false malware claims |
| SaaS fleet platform first | Portfolio clarity suffers without deterministic core |

## Consequences

- Positive: FAANG + Big 4 reviewers see bounded, testable system  
- Negative: Less flashy than “AI security”; requires demo discipline  

## Security considerations

Policy gates block kill/firewall/adapter paths. AI does not authorize execution.

## Audit considerations

Hash-chained JSONL + governance report with `limitations_and_non_claims`. Not formal attestation.

## What this prevents

- Silent registry mutation in default paths  
- Malware accusations from listener correlation alone  

## What this does not prove

- Regulatory compliance  
- Enterprise-wide control effectiveness without population testing  

## Interview defense

> “I chose an evidence pipeline because repair without proof creates operational and audit risk. The product shows how reliability incidents become control-tested, replayable governance artifacts — remediation is explicitly gated.”
