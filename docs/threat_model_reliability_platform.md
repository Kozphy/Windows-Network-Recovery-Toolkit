# Threat Model — Endpoint Reliability Platform

## Assets

| Asset | Sensitivity |
|-------|-------------|
| `platform_events.jsonl` | Medium — endpoint telemetry, may include process paths |
| `platform_decisions.jsonl` | High — policy outcomes, hypothesis labels |
| Audit HMAC signatures | High — tamper detection integrity |
| Operator RBAC headers | Medium — demo mode; production must use Entra/API keys |
| PostgreSQL tables | High — fleet-wide event/decision history |

## Trust boundaries

1. **Endpoint agent → API** — TLS + API key in production; demo uses localhost.
2. **API → storage** — append-only writes; no in-place mutation of decisions.
3. **Operator UI → API** — RBAC headers; viewers cannot trigger previews.

## Threats & mitigations

| Threat | Impact | Mitigation |
|--------|--------|------------|
| Forged high-confidence hypothesis | Unauthorized remediation | Policy defaults PREVIEW; ALLOW requires proof + confirmation |
| Audit log tampering | False compliance | HMAC-SHA256 on `PlatformDecisionRecord`; verify endpoint |
| Replay injection | Wrong historical state | Events keyed by `event_id`; replay loads stored rows only |
| Privilege escalation via RBAC headers | Cross-tenant access | Replace demo headers with JWT/Entra in production |
| Destructive action via API | Host damage | `blocked_actions` in policy; no silent kill/firewall reset |
| Malware false positive auto-block | Developer outage | Malware hypothesis capped at PREVIEW without proof tier |

## Out of scope (explicit)

- Kernel-level rootkit detection
- Automatic process termination without admin elevation
- Cross-tenant fleet isolation (requires multi-tenant auth layer)

## Residual risk

Ordinal confidence scores may be misread as probability by operators. UI and API responses include `limitations` arrays reinforcing epistemic boundaries.
