# Agent next-step planner

The agent next-step planner recommends the next read-only diagnostic step or preview action based on the latest stored diagnosis. It runs locally, never mutates Windows state, and writes its own audit row for every recommendation.

## Surfaces

| Surface | Description |
| --- | --- |
| `python -m src agent next-step --json` | CLI entry that consumes the latest stored `DiagnosisResult` (or one referenced by `--run-id`). |
| `POST /platform/agent/next-step` | FastAPI route that returns the same shape with audit chaining. |

Both paths share `platform_core.agent_planner.plan_next_step` so they cannot drift.

## Capabilities

- `suggest_next_probe`
- `rank_hypotheses`
- `explain_risk`
- `recommend_preview_action`
- `summarize_audit`
- `identify_missing_evidence`

## Forbidden

The planner is never allowed to:

- Execute repairs.
- Change registry values.
- Kill processes.
- Reset the firewall.
- Disable adapters.
- Delete certificates.
- Run arbitrary shell commands.

## Response contract

```json
{
  "next_step": "run_diagnosis | run_proxy_disable_preview | inspect_node_process | run_registry_writer_proof | restart_browser | collect_lkg | compare_proxy_config | review_audit",
  "reason": "...",
  "evidence_used": ["..."],
  "confidence": 0.0,
  "policy_boundary": "recommendation_only_no_mutation",
  "blocked_actions": [
    "process_kill",
    "firewall_reset",
    "adapter_disable",
    "adapter_reset",
    "winsock_reset",
    "certificate_delete",
    "broad_registry_cleanup",
    "arbitrary_shell"
  ],
  "audit_event_id": "..."
}
```

`policy_boundary` is fixed; callers that observe a different value should treat the response as malformed. `blocked_actions` is included on every response so operators can confirm at a glance which destructive action_ids the planner is prevented from emitting.

## Decision logic

The planner is deterministic and intentionally narrow:

| Condition | Recommendation |
| --- | --- |
| No stored diagnosis | `run_diagnosis` |
| `wininet_proxy_state` shows a localhost proxy and proof status is not confirmed | `run_registry_writer_proof` |
| Goal `recommend_preview_action` and confidence ≥ 0.6 | `run_proxy_disable_preview` |
| Goal `summarize_audit` | `review_audit` |
| Goal `identify_missing_evidence` with gaps | `run_diagnosis` (with the gap descriptor as `reason`) |
| Localhost proxy without conflicting proof | `inspect_node_process` |
| Otherwise | `compare_proxy_config` |

The planner clearly states uncertainty in `reason`; it never claims maliciousness without proof.

## Audit

Every recommendation appends one row to `logs/safety_audit.jsonl` (CLI) or to the platform `audit.jsonl` (backend) with `event_kind: agent_next_step_requested`, the goal, the recommended next step, and the blocked-action list.
