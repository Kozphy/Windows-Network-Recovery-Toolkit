# Design Principles

This project is intentionally small and practical.

## Goals

- Help non-expert users diagnose common Windows network failures.
- Use built-in Windows tools only.
- Provide clear recommendations instead of raw command output alone.
- Keep repair actions understandable and reversible where possible.
- Make the repository useful as both a tool and a portfolio project.

## Non-Goals

- Replace professional network administration tools.
- Troubleshoot every possible router, ISP, or enterprise policy issue.
- Modify advanced adapter bindings.
- Automatically reset firewall rules.
- Install third-party dependencies.

## User Experience

Scripts should:

- Explain what they are doing.
- Print clear status messages.
- Ask before risky changes.
- Tell users when a restart is required.
- Avoid hidden behavior.

## Automation Strategy

The project separates diagnosis from repair:

- `auto_diagnose.bat` collects evidence and recommends a path.
- `auto_fix.bat` asks before applying the recommended repair.
- Targeted repair scripts solve narrow problems.
- `one_click_fix.bat` remains the full fallback.

This keeps the default path safe while still giving users a fast repair option.

## Decision Logic

The automatic diagnosis checks network layers in order:

1. DNS resolution
2. Proxy configuration
3. TCP port 443 connectivity
4. HTTPS request behavior
5. Browser-specific possibility

The result is intentionally simple. It recommends the next useful action, not a perfect root-cause analysis.

## Documentation Standard

Documentation should be:

- Beginner-friendly
- Specific
- Short enough to scan
- Clear about risks
- Consistent with script behavior

When script behavior changes, update the README and related docs in the same change.

Language-specific conventions observed in-repo (do not retrofit unrelated style churn):

| Language | Standard | Applies to |
| --- | --- | --- |
| Python | Google-style module + public API docstrings; explicit **Raises**, **Returns**, side effects, Audit Notes only on mutation / SOC paths | `src/`, `failure_system/`, `platform_core/`, `evidence/`, `endpoint_agent/`, … |
| TypeScript / React | File-level **`@file` / `@remarks`** where routes or UX imply safety/posture boundaries; summarize components that ship to users | `frontend/` Next.js surfaces |
| PowerShell | Comment-based help (`.SYNOPSIS`, `.DESCRIPTION`, `.NOTES` with privileges, side effects, recovery) plus inline purpose comments | `scripts/*.ps1` |
| Batch / CMD | Leading `REM` blocks: purpose, privileges, mutations, artifact paths (`reports/`, `logs/`) | `scripts/*.bat` |
| Markdown | Architecture, sequencing, troubleshooting, reviewer audit maps | `docs/`, root `README.md`, `SECURITY.md` |

**Engineering Notes** paragraphs appear only where trade-offs materially affect maintainability (portfolio scope vs scalable designs).

**Audit Notes** appear on append-only logs, remediation execution, subprocess/system mutation, RBAC gates, or headers that spoof identity in demos—not on pure helpers.

No Go/Rust crates ship in-tree; adopt idiomatic Rustdoc/`///` and Go package comments **if** such code is introduced later without relaxing “document what exists only” discipline.

## Repository documentation map

High-signal Markdown references (paths relative to repository root):

| Area | Doc |
| --- | --- |
| Beginner scripts + Python CLI overview | `README.md` |
| Failure Knowledge System layers + contract | `docs/architecture.md`, `docs/failure_block_contract.md`, `docs/interview_pitch.md` |
| Decision scoring contract (live/v2) | `docs/decision_engine_v2.md` |
| Hybrid FastAPI agent + repair policy | `network_agent/api.py` module docstring + `docs/system_architecture.md` |
| SaaS demo backend (SQLite + Stripe surfaces) | `backend/README.md`, `backend/main.py` module docstring |
| Operational troubleshooting | `docs/operational_runbook.md`, `docs/troubleshooting_flow.md` |
| Proxy-first failures | `docs/proxy_error.md`, `docs/ping_ok_but_browser_fails.md` |
| Safety boundaries | `docs/safety_model.md`, `SECURITY.md` |

Python modules added for structured FailureBlocks document responsibilities inline (`failure_system/` package).
