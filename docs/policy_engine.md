# Policy gate engine

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
