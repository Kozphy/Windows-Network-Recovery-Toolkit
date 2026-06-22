# Case 003 — Healthy local proxy

**Fixture:** `examples/evidence/LOCAL_PROXY_ACTIVE.json` (or known dev proxy fixture)

## Symptom

Proxy configured on localhost; connectivity works as expected for dev tooling.

## Evidence

- WinINET points to localhost port
- Listener present (e.g. dev proxy on 59081)
- TLS/path checks pass for intended dev use

## Known / Not proven

| Known | Not proven |
|-------|------------|
| Local proxy is intentional and listening | Enterprise approval for that proxy binary |
| Classification should not escalate to incident | Absence of shadow IT review |

## Classification

- **Primary:** `KNOWN_DEV_PROXY` or healthy-proxy equivalent
- **Secondary:** minimal risk signals
- **Proof tier:** T2+ when listener confirmed

## Control test

PASS when listener matches configured port and policy allows dev proxy.

## Policy

No remediation — monitor or accept classification.

## Human review

Typically not queued unless false-positive workflow triggered.

## Audit artifact

Negative case for benchmark — prevents false escalation.

## Governance value

Demonstrates **false escalation prevention** in classifier evaluation harness.

## Limitations

Healthy proxy ≠ approved corporate standard. Management information only.

## Interview talking point

*"Golden fixtures include negative cases so we measure false escalation, not just detection rate."*
