# ADR-0002: Policy-Gated Remediation

## Status

Accepted

## Context

Registry mutation, process termination, and network stack resets on developer laptops create outage and evidence-destruction risk. Automated remediation without gates fails ITGC change-management expectations and platform safety reviews.

## Decision

All destructive or state-changing remediation defaults to **preview-only**:

- CLI: `proxy-disable --dry-run` default `true`
- Typed confirmation token required for apply (e.g. `DISABLE_WININET_PROXY`)
- `SAFE_REMEDIATION_POLICY` control test documents read-only health/watch defaults
- Policy outcomes: `PREVIEW_ONLY`, `REQUIRE_HUMAN_REVIEW`, `BLOCK`
- `execution_authority` distinct from `policy_action` in audit and Power BI export

No automatic process kill or silent registry write in health pipeline.

## Alternatives considered

| Alternative | Why rejected |
|-------------|--------------|
| Auto-disable on HIGH risk | Confidence is ordinal; false positives would break dev workflows |
| Boolean `--confirm` flag | Too easy to script; typed phrase forces deliberate action |
| Remediation without audit | Breaks hash chain reconstruction |

## Consequences

- Operators need extra step for live apply — mitigated by clear preview JSON
- FAIL control tests recommend preview, not auto-fix
- API routes must mirror same gates when implemented

## Security considerations

- Preview output must not contain credentials from rollback snapshots
- Apply path must log before/after state to audit JSONL
- Reverter loops may restore settings after apply — watch must continue

## Audit considerations

- CTRL-009 maps to this ADR
- Auditors can reperformance dry-run without production impact
- Limitation: toolkit cannot enforce operator actions outside CLI

## What this prevents

- Silent registry mutation during diagnosis
- Autonomous remediation from classification alone
- "Helpful" scripts that destroy attribution evidence

## What this does not prove

- That operators always use gated commands (shell bypass possible)
- That previewed changes are correct for all corporate policies
- Change advisory board approval (organizational control)

## Interview defense

"We default dry-run because recommendation is not execution authority. HIGH risk means human review, not auto-disable. That's the same pattern I'd use for internal platform runbooks."
