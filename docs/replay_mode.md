# Replay mode

CLI:

```powershell
python -m platform_core.replay --input platform_data/normalized_events.jsonl --json
```

Semantics:

1. Streams JSON lines without mutating disks beyond read handles.
2. Skips malformed lines (counts `parse_errors`).
3. Rows with `signals.remediation_action` (or alias `recommended_action`) are re-evaluated through `evaluate`.
4. When a stored `policy_decision` exists, replay compares canonicalized payloads to detect drift.

Outputs:

| Counter | Interpretation |
| --- | --- |
| `changed_decisions` | Historical vs recomputed divergence |
| `newly_blocked_execute` | Executes previously labelled allowed now blocked |
| `newly_allowed_preview` | Preview previously blocked now allowed |

API equivalent: `POST /platform/replay/preview` with inline `events[]` (**no filesystem path parameters**).
