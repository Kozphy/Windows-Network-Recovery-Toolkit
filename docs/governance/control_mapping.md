# Control Mapping (Informational)

Not a formal SOC2 certification. Maps policy outcomes to ITGC-style control categories.

| Policy outcome | Controls |
|----------------|----------|
| ALLOW | Prevent, Audit |
| PREVIEW_ONLY | Detect, Audit |
| REQUIRE_HUMAN_APPROVAL | Approve, Prevent, Audit |
| BLOCK | Prevent, Detect, Audit |
| ROLLBACK_REQUIRED | Recover, Audit |

Implementation: `src/platform_core/governance/control_mapping.py`
