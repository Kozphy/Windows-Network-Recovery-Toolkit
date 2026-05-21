# Policy gate engine

## Policy v2 reason codes (`platform_core/policy_v2.py`)

Canonical uppercase codes for reasoning runs, hypothesis rows, and dashboards:

| Code | Meaning |
| --- | --- |
| `HIGH_CONFIDENCE_UNPROVEN` | Heuristic confidence is high but proof is not CONFIRMED — stays PREVIEW |
| `CONFIRMED_SAFE_TIER_WITH_CONFIRMATION` | CONFIRMED proof + operator confirmation — may ALLOW safe-tier registry actions |
| `DESTRUCTIVE_ACTION_BLOCKED` | Firewall reset, adapter disable, kill, arbitrary shell |
| `REQUIRES_OPERATOR_CONFIRMATION` | Preview/dry-run until explicit confirmation |
| `CONFLICTING_SIGNALS` | Observations contradict — downgrade to PREVIEW |

Every `PolicyDecision` from `evaluate_reasoning_policy` includes `blocked_actions` (defaults to `ALWAYS_BLOCKED_ACTIONS`).

Example envelope:

```json
{
  "decision": "PREVIEW",
  "reason_codes": ["HIGH_CONFIDENCE_UNPROVEN", "REQUIRES_OPERATOR_CONFIRMATION"],
  "blocked_actions": ["firewall_reset", "process_kill", "adapter_disable"]
}
```

## Classic + structured gate (unchanged behavior)

Two layers coexist intentionally:

## Classic (`policy/classic.py`)

`evaluate_action` encodes remediation registry tiers (forbidden/high blocks, surfaces, org policy knobs). Stateless and **does not** consider operator JWT-style roles.

## Gate (`policy/engine.py`)

`evaluate(signal_snapshot, remediation_action, operator_context)` adds:

| Output | Meaning |
| --- | --- |
| `preview_allowed` | Operator dashboards may derive preview rows |
| `execute_allowed` | **Only true for `admin` role**, allowlisted `.bat`, confirmation phrase enforced downstream |
| `reason_codes | machine diffable rationales |

Rules of thumb:

- **Default deny live execution for operators** (matches `rbac.py` demos).
- **Firewall / arbitrary command** pathways stay blocked independently of previews.
- **Proxy resets** inherit registry confirmation phrases (`RUN_PROXY_RESET`).

See remediation registry (`platform_core/remediation_registry.py`) for canonical action metadata—**the registry is authoritative**.
