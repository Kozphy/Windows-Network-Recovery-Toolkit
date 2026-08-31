# OpenClaw local configuration (examples only)

This directory holds **example** OpenClaw configuration for the WNRT coding agent.

| File | Purpose |
| ------ | --------- |
| `openclaw.example.json5` | Documented sandboxed agent config — copy locally; do not commit secrets |
| `task.example.json` | Example approved low-risk task for `scripts/openclaw_task_runner.py` |
| `runs/` | Local audit JSON (gitignored; never commit) |

## Setup

1. Install OpenClaw and Docker per [docs/openclaw-coding-agent.md](../docs/openclaw-coding-agent.md).
2. Clone this repository into an **isolated** workspace directory (not your daily secrets home).
3. Copy `openclaw.example.json5` into your OpenClaw config location and set `workspace` to that isolated clone.
4. Ensure the `wnrt-coder` skill is available to the agent (repo `skills/wnrt-coder/`).
5. Run `openclaw doctor` and enable sandboxing before any automated task.

## Non-negotiables

- No real tokens, usernames, or private absolute paths in committed files
- Sandbox `network: "none"` by default
- Never mount Docker socket into the agent sandbox
- Draft PRs only; humans merge after CI
