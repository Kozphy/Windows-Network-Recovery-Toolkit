# OpenClaw coding agent (WNRT)

Controlled development automation for this repository. OpenClaw may analyze **approved**
tasks, edit code in an isolated branch, run validation, and open a **draft** pull request.

OpenClaw generates candidate changes. Passing tests does not prove that the code is free of
defects or safe for production.

## Architecture

```text
approved task (JSON or GitHub issue + agent-ready)
  → scripts/openclaw_task_runner.py (policy gate)
  → branch agent/openclaw/<task-id>-<slug>
  → OpenClaw agent wnrt-coder (sandboxed) edits code
  → staged validation (ruff / pytest / optional full suite)
  → commit + push branch
  → draft pull request only
  → human review + CI
  → audit JSON under .openclaw/runs/ (gitignored)
```

Governance stages remain separate:

`Observation → Hypothesis → Proof → Policy → Stakeholder → Timing → Preview → Approval → Execution → Audit → Replay`

Policy permission is not a safety guarantee. Dry-run / preview-only remediation stays the default.

## What the agent may do

- Read issues marked ready for automation (`agent-ready` + explicit approval)
- Inspect repository code, docs, and tests
- Create `agent/openclaw/*` branches
- Write or modify code and tests within allowlisted paths
- Run lint, format checks, type checks, security scans, and tests
- Commit validated changes and open **draft** PRs
- Emit a structured audit summary (no secrets)

## What the agent must not do

- Push directly to the default branch
- Merge pull requests or enable auto-merge
- Deploy applications or change production systems
- Execute live Windows registry, proxy, firewall, adapter, process, or network remediation
- Access `.env`, SSH keys, API tokens, deployment secrets, credentials, or private audit exports
- Weaken, remove, skip, or bypass safety-contract tests
- Silently change CI, deployment, security, or branch-protection behavior

## Installation prerequisites

- Python 3.11+
- Git and [GitHub CLI](https://cli.github.com/) (`gh`) for draft PRs
- [Docker](https://docs.docker.com/) for the OpenClaw sandbox backend
- [OpenClaw](https://docs.openclaw.ai/) installed so `openclaw doctor` succeeds
- An **isolated** clone of this repository as the agent workspace (not your secrets home)

## Windows setup

1. Install Docker Desktop and confirm `docker version` works.
2. Install OpenClaw per upstream docs; run `openclaw doctor`.
3. Clone this repo to a dedicated path, for example `C:\OpenClaw\workspaces\wnrt` (placeholder only).
4. Set `PYTHONPATH` to the repo root when running toolkit or runner scripts:

   ```powershell
   $env:PYTHONPATH = (Get-Location).Path
   ```

5. Copy `.openclaw/openclaw.example.json5` into your local OpenClaw config and set `workspace`
   to the isolated clone. Do not commit real tokens or private absolute paths.

## OpenClaw onboarding

1. Enable the `wnrt-coder` skill from `skills/wnrt-coder/SKILL.md`.
2. Configure a single agent id: `wnrt-coder` (see example config).
3. Confirm sandbox mode is `all`, backend `docker`, scope `session`, `workspaceAccess: rw`.
4. Keep Docker `network: "none"`, `readOnlyRoot: true`, `capDrop: ["ALL"]`.
5. Do **not** mount the host Docker socket or credential directories into the sandbox.

## Isolated workspace

- Use a clean clone with no `.env`, no SSH agent forwarding into the sandbox, and no deploy keys
  beyond the least-privilege GitHub token described below.
- Point OpenClaw `workspace` / repo root at that clone only.
- Prefer fixture-based work (`tests/fixtures/`) over live host speculation.

## Creating an approved task

### Local JSON

See `.openclaw/task.example.json`:

```json
{
  "task_id": "123",
  "title": "Add proxy evidence export validation",
  "description": "Clear acceptance criteria",
  "approved": true,
  "risk_level": "low",
  "allowed_paths": ["windows_network_toolkit/", "tests/", "docs/"],
  "forbidden_paths": [".github/workflows/deploy.yml", ".env", "platform_data/", ".audit/"]
}
```

Only `low` and `medium` risk levels are eligible for automatic execution. `high` / `critical`
require manual work and are rejected by the runner.

### GitHub issue

- Label: `agent-ready`
- Body markers (recommended):

```text
approved: true
risk_level: low
allowed_path: docs/
```

Optional label `agent-approved` also counts as approval when using the issue loader.

## Running the agent manually

Policy check / plan only:

```powershell
$env:PYTHONPATH = (Get-Location).Path
python scripts/openclaw_task_runner.py --task-json .openclaw/task.example.json --dry-run
```

Create isolated branch (from default), then run OpenClaw `wnrt-coder` against the task,
then validate:

```powershell
python scripts/openclaw_task_runner.py --task-json .openclaw/task.example.json --create-branch
# ... OpenClaw session edits code on agent/openclaw/<id>-<slug> ...
python scripts/openclaw_task_runner.py --task-json .openclaw/task.example.json --validate
```

Draft PR after successful validation (requires `gh` auth and a pushed branch):

```powershell
python scripts/openclaw_task_runner.py --task-json .openclaw/task.example.json --validate --create-draft-pr
```

Commit message format: `agent: <concise change summary>`
Draft PR title: `[OpenClaw Draft] <task title>`

## Inspecting the generated branch

```powershell
git fetch origin
git checkout agent/openclaw/<task-id>-<slug>
git log --oneline -n 10
git diff Multi_Domain_Decision_Platform...HEAD
```

## Reviewing the draft pull request

1. Confirm the PR is **draft** and targets `Multi_Domain_Decision_Platform` (or documented default).
2. Read Summary, Validation, Risks, Limitations, and Rollback sections.
3. Wait for CI on `.github/workflows/ci.yml`.
4. Merge only after human review — never rely on the agent to merge.

## Validation pipeline

**Stage 1 (targeted):** `ruff check` / `ruff format --check` on touched roots; targeted `pytest`.

**Stage 2 (optional `--full-validate`):** repository ruff, scoped mypy, bandit, broader pytest.

The runner refuses to create a draft PR when lint, format, required tests, safety-contract
checks, prohibited paths, secret-path touches, oversized diffs, or default-branch targeting fail.

Configurable limits (defaults): max **20** files, max **1500** changed lines
(`--max-files`, `--max-lines`).

## Audit output

Runs write JSON under `.openclaw/runs/` (gitignored) with schema `openclaw_coding_run.v1`.
Do not commit live audit logs.

## GitHub permissions (least privilege)

Preferred token / app permissions:

| Scope | Access |
| ------- | -------- |
| Contents | read/write (feature branches) |
| Pull requests | read/write (draft create) |
| Issues | read |
| Metadata | read |
| Workflows | read-only |
| Deployments | **none** |
| Administration | **none** |
| Secrets | **none** |

The coding agent must not be able to merge PRs, modify branch protection, modify repository
secrets, trigger production deployment, or administer the repository.

Where GitHub cannot distinguish pushing a branch from pushing the default branch, rely on
**branch protection** plus the task runner’s branch policy (`agent/openclaw/*` only).

## Security boundaries

- Sandbox network disabled by default
- No elevated tool execution / no Docker socket in the agent sandbox
- No host credential directory mounts
- Forbidden paths include `.env`, `.audit/`, `platform_data/`, deploy workflows
- Live remediation keywords are blocked in task text

## Limitations

- OpenClaw is not a substitute for human design review or security review.
- Full CI may still fail after local stage-1 validation.
- Keyword policy is heuristic; ambiguous tasks should be stopped and clarified.
- Network-disabled sandboxes cannot fetch packages; prepare the environment outside the agent.

## Troubleshooting

| Symptom | Check |
| --------- | -------- |
| `policy_blocked` | `approved`, risk level, forbidden phrases, allowlisted paths |
| `stage1_failed` | ruff / pytest output in runner JSON |
| Draft PR failed | `gh auth status`, branch pushed, base branch name |
| Sandbox errors | Docker running; `openclaw doctor`; network/binds in config |

## Emergency stop

Stop the OpenClaw gateway immediately:

```powershell
openclaw gateway stop
```

Then:

1. Disable or remove the `wnrt-coder` agent entry from your local OpenClaw config.
2. Revoke the GitHub personal access token or GitHub App installation used by the agent.
3. Close any open draft PRs that should not proceed.
4. Delete or quarantine `agent/openclaw/*` branches if needed.

## Related files

| Path | Role |
| ------ | ------ |
| `skills/wnrt-coder/SKILL.md` | Agent skill instructions |
| `.openclaw/openclaw.example.json5` | Example sandboxed config |
| `scripts/openclaw_task_runner.py` | Policy + validation + draft PR helper |
| `src/platform_core/openclaw/` | Policy models and audit |
| `tests/test_openclaw_task_policy.py` | Safety-policy unit tests |
| `docs/ci-cd.md` | CI/CD and default branch notes |
