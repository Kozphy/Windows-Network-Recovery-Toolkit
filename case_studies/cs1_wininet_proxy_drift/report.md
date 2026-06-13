# CS1 Report: WinINET Proxy Drift

## Executive Summary

Classification: **DEAD_PROXY_CONFIG** (ordinal 0.92 heuristic score, not probability).  
Proof conclusion: **supported**.  
Principle compliance: **all four principles satisfied**.

## Evidence Chain

| Tier | Signal | Value | Note |
|------|--------|-------|------|
| OBSERVATION | wininet_proxy_enabled | true | Registry read — not proof |
| OBSERVATION | listener_found | false | Netstat — not proof |
| PROOF_ATTEMPT | localhost_listener_check | failed | No listener on configured port |
| PROOF_ATTEMPT | wininet_winhttp_comparison | supported | Browser path differs from WinHTTP |
| PROOF_CONCLUSION | conclusion | supported | Structured proof — not certainty |

## Blocked Overclaims

- Does not prove malware without writer telemetry.
- Does not prove MITM without TLS/path proof.
- Listener correlation is not registry-writer causation.

## Principle Compliance

| Principle | Status |
|-----------|--------|
| Observation is not proof | Pass |
| Correlation is not causation | Pass |
| Confidence is not certainty | Pass |
| Policy permission is not a safety guarantee | Pass |

## Limitations

- Does not prove malware or MITM.
- Heuristic confidence is ordinal — not probability.
- Principle compliance does not guarantee endpoint safety.

## Safe Remediation Controls

- Dry-run default
- Typed confirmation: `DISABLE_WININET_PROXY`
- Rollback snapshot before apply
- Post-change `proxy-watch` monitoring
- Append-only audit JSONL
