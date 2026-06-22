# Case 001 — Dead localhost proxy

**Fixture:** `examples/evidence/DEAD_PROXY_CONFIG.json` · `real_evidence/case-001-dead-proxy/`

## Symptom

Browser shows `ERR_PROXY_CONNECTION_FAILED`; ping and DNS still succeed.

## Evidence

- WinINET proxy enabled → `127.0.0.1:59081`
- WinHTTP direct access enabled (mismatch)
- No listener on localhost:59081

## Known / Not proven

| Known | Not proven |
|-------|------------|
| Stale WinINET proxy points at dead localhost port | Malware or MITM |
| Browser path fails while ICMP/DNS may work | Which process last wrote the proxy key |

## Classification

- **Primary:** `DEAD_PROXY_CONFIG`
- **Secondary:** `WININET_WINHTTP_MISMATCH`, `DEAD_LOCALHOST_PORT`
- **Proof tier:** T2–T3 (listener absent; writer optional)

## Control test

Proxy configuration control — FAIL when listener missing with proxy enabled.

## Policy

`DISABLE_WININET_PROXY` → **PREVIEW_ONLY** (dry-run default).

## Human review

Recommended when classification is accusatory-adjacent or remediation preview requested.

## Audit artifact

Evidence pack JSON + optional `incidents.jsonl` hash chain.

## Governance value

Separates **connectivity symptom** from **security verdict** — committee-safe narrative.

## Limitations

Does not prove malware or MITM. Classification is not accusation.

## Interview talking point

*"We cap claim strength with proof tiers and explicit limitations — reliability triage, not EDR."*
