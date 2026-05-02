# FailureBlock contract

**FailureBlocks** are JSON-serializable records produced by the `failure_system` package. They summarize one diagnostic pass for **local** search, APIs, and operator review.

Authoritative schema: `failure_system/models.py` (`FailureBlock`).

## Fields

| Field | Type | Purpose |
| --- | --- | --- |
| `id` | UUID | Stable identifier for APIs and deduplication (generated per block). |
| `name` | string | Short title (often derived from top rule cause). |
| `symptom` | string | Human-readable symptom line for this snapshot. |
| `observed_signals` | list[str] | Compact tags (e.g. `ping_ip=ok`). |
| `likely_causes` | list[str] | Ranked hypothesis labels from rule outcomes. |
| `diagnostic_commands` | dict[str, str] | Probe key → merged stdout/stderr text (**truncated** by collector). Treat as **sensitive** if copied off-host. |
| `confidence_score` | float | Primary hypothesis confidence in `[0.0, 1.0]` (clamped in model). |
| `recommended_fix` | string | **Narrative** guidance only—does not execute repairs. |
| `risk_level` | enum | `low` / `medium` / `high` — severity of the **recommended human action**, not outage SLA. |
| `safety_boundary` | string | States what automated repair this layer does **not** perform. |
| `rollback_plan` | string | How to undo or mitigate if the operator applies a suggested fix elsewhere. |
| `created_at` | datetime (UTC) | Time the block was generated. |
| `source_logs` | list[str] | Compact provenance (rule ids, clipped explanations)—not raw OS logs. |

## Storage

- One JSON object **per line** in `data/failure_blocks/YYYY-MM-DD.jsonl` (append-only).
- Shards are **gitignored** by default—see root `.gitignore` and `docs/safety_model.md`.

## Safe fictional example

No real hostnames, IPs, or corporate domains:

```json
{
  "id": "11111111-1111-4111-8111-111111111111",
  "name": "DNS resolution failure",
  "symptom": "Ping OK but DNS lookup fails.",
  "observed_signals": [
    "ping_ip=ok",
    "nslookup=fail",
    "curl_https=fail",
    "winhttp_direct=yes",
    "proxy_line=no",
    "intermittent_reported=no"
  ],
  "likely_causes": [
    "DNS resolution failure",
    "HTTPS/application-path failure (proxy, TLS, filter, or browser stack)"
  ],
  "diagnostic_commands": {
    "nslookup_example": "Simulated non-authoritative answer for example.test domain."
  },
  "confidence_score": 0.88,
  "recommended_fix": "Review resolver configuration and toolkit DNS guidance; run targeted repair scripts only after confirmation.",
  "risk_level": "low",
  "safety_boundary": "Failure Knowledge System runs read-only diagnostics only; repairs require separate operator action.",
  "rollback_plan": "Restore prior static DNS entries if you changed them during manual remediation.",
  "created_at": "2026-01-15T14:30:00+00:00",
  "source_logs": [
    "rules:dns_failure_likely",
    "explain:Simulated rule explanation text for documentation."
  ]
}
```

## Versioning

Schema evolution should remain backward-compatible for JSONL readers or include migration notes when fields change.
