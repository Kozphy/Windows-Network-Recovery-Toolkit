# HAR redaction

Before comparison or logging, HARs are deep-copied and secrets are removed.

## Always redacted

| Field | Treatment |
| ------- | ----------- |
| `Cookie` header value | `[REDACTED]` (presence retained) |
| `Set-Cookie` value | `[REDACTED]` (count retained) |
| `Authorization` / `Proxy-Authorization` | `[REDACTED]` |
| Request/response bodies | Replaced with `[REDACTED]` |
| Query params matching `token\|key\|secret\|code\|session\|auth\|jwt\|sig\|signature` | `[REDACTED]` |

## Retained for diagnosis

- URL path (with sensitive query params scrubbed)
- Method, status, redirect URL
- Boolean cookie-header presence / Set-Cookie count
- Timing, blocked-by-client flags, service-worker flags

## Operator note

Export HARs yourself from DevTools; the toolkit never decrypts Chromium cookie databases.
