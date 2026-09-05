# Local operator SLOs (not fleet error budgets)

**Status:** Defined for a single Windows endpoint / operator workstation. Not a 99.9% availability claim. No PagerDuty in this prototype.

See [google-l11-reference.md](google-l11-reference.md) (L6 substance) and [production-readiness-gap.md](production-readiness-gap.md).

## SLIs

| SLI | Meaning | Source | Target (local operator) |
| ----- | --------- | -------- | ------------------------- |
| Time-to-direct after rewrite | Detect localhost WinINET rewrite → preview/apply direct | `rewrite_detected` + `recovered_at` in platform JSONL | Measure first; aim minutes, not hours |
| False-clear rate | Proxy classified healthy while path-health or browser-stall still degraded | `proxy_healthy_path_degraded` vs `proxy_healthy_path_ok` | Drive toward 0 via `operator-incident` |
| Dual-stack path success | IPv4 vs IPv6 HTTPS probe outcomes | `path_health_ipv4` / `path_health_ipv6` | IPv4 success when IPv6 is broken is expected; do not treat IPv6 fail as malware |
| Blocked high-risk actions | Policy engine blocked execute | `audit.jsonl` `decision=blocked` | Must stay non-zero capable; silent kill remains blocked |

Null values mean **unmeasured**, not a pass. `slo_limitations[]` on `SloMetrics` records that.

## What this is not

- Not a fleet SLO or multi-tenant error budget ([ADR-008](adr/ADR-008-fleet-scale-100k-endpoints.md) stays Proposed).
- Not an ISP uptime SLA.
- Not a security detection KPI.

## Operator wiring

`python -m src operator-incident` sets `sli_hints` on the incident card so the primary class maps to the SLI it affects.

Compute snapshot: `GET /platform/slo` (demo) or `compute_slo_metrics()` in [`platform_core/reliability_metrics.py`](../platform_core/reliability_metrics.py).
