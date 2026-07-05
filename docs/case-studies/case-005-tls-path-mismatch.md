# Case 005 — TLS path mismatch

**Fixture:** `tests/fixtures/enert/tls_cert_mismatch.json`

## Symptom

HTTPS fails or warns while plain connectivity appears fine — certificate or path mismatch.

## Evidence

- TLS handshake metadata vs expected corporate path
- Possible proxy MITM **symptom** — not verdict
- Listener and WinINET context from fixture

## Known / Not proven

| Known | Not proven |
|-------|------------|
| Certificate or path inconsistent with expected profile | Confirmed MITM attack |
| Browser TLS error correlates with proxy path | Corporate root CA deployment status |

## Classification

- **Primary:** TLS/path mismatch class (fixture-aligned)
- **Secondary:** proxy and listener signals
- **Proof tier:** T2–T3 with explicit cap without full chain capture

## Control test

TLS path control — FAIL/PARTIAL per fixture expectations.

## Policy

No automatic firewall or adapter changes.

## Human review

Queue when narrative approaches security incident language.

## Audit artifact

ENERT fixture + analytics pipeline JSON output.

## Governance value

Teaches **epistemic boundaries** — TLS anomaly ≠ MITM confirmed.

## Limitations

Does not prove MITM. AI explanations pass `explanation_guardrails`.

## Interview talking point

*"Forbidden phrase scanner in classifier benchmark keeps outputs committee-safe."*
