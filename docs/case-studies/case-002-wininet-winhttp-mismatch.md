# Case 002 — WinINET / WinHTTP mismatch

**Fixture:** `examples/evidence/WININET_WINHTTP_MISMATCH.json`

## Symptom

Some apps use system proxy; others bypass — inconsistent connectivity.

## Evidence

- WinINET proxy server configured
- WinHTTP `direct access` or different proxy path
- Split behavior between WinINET and WinHTTP consumers

## Known / Not proven

| Known | Not proven |
|-------|------------|
| Dual-stack proxy configuration drift | Intentional enterprise policy vs local corruption |
| Apps disagree on egress path | Attacker manipulation |

## Classification

- **Primary:** `WININET_WINHTTP_MISMATCH` (or secondary on dead-proxy cases)
- **Secondary:** context-dependent listener/proxy signals
- **Proof tier:** T1–T2

## Control test

Configuration consistency control — PARTIAL/FAIL when stacks diverge.

## Policy

Preview-only remediation; no automatic registry merge.

## Human review

Queue when override or cross-stack remediation preview requested.

## Audit artifact

Fixture replay + governance report row.

## Governance value

Explains **why ping works but browser fails** without security-product language.

## Limitations

Does not prove malware. Policy permission is not a safety guarantee.

## Interview talking point

*"Full before/after classification avoids false positives when localhost is removed but remote proxy remains."*
