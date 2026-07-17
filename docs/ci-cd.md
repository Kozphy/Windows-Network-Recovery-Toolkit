# CI/CD guide

This repository is a **Python 3.11** monorepo (FastAPI backend, CLI toolkits, Next.js frontend) with **Docker Compose** for production-shaped local and VM deployment.

| Layer | Tooling |
|-------|---------|
| Language | Python 3.11+, TypeScript (Next.js 14) |
| Package manager | `pip` + editable install (`pip install -e ".[dev]"`) |
| Config | `pyproject.toml`, `pytest.ini`, `Makefile` |
| Lint | Ruff (`ruff check`, `ruff format --check`) |
| Type-check | Mypy (scoped portfolio modules — see Makefile) |
| Tests | pytest |
| Build | Docker (`Dockerfile`), `npm run build` in `frontend/` |
| Deploy | GHCR image + SSH compose deploy (`build.yml`, `deploy.yml`) |

---

## Local development

### Prerequisites

- Python **3.11+**
- Node.js **20** (frontend only)
- Docker (optional — compose smoke / prod demo)
- Git

### Install dependencies

```powershell
cd Windows-Network-Recovery-Toolkit
python -m venv .venv
.\.venv\Scripts\Activate.ps1   # Windows
# source .venv/bin/activate    # Linux/macOS

python -m pip install --upgrade pip
pip install -e ".[dev]"
```

Set `PYTHONPATH` to the repo root when using `python -m src`:

```powershell
$env:PYTHONPATH = (Get-Location).Path
```

### Run locally

```powershell
# Read-only proxy check (fixture — works off Windows too)
python -m windows_network_toolkit proxy-status --fixture examples/evidence/DEAD_PROXY_CONFIG.json

# FastAPI (fixture/demo mode)
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000

# Next.js dashboard
cd frontend && npm ci && npm run dev
```

### Test, lint, type-check (Makefile parity)

```powershell
make install      # pip install -r requirements.txt (editable dev extra recommended above)
make lint         # ruff check .
make verify-format # ruff format --check .  (add to Makefile habit)
make typecheck    # mypy on portfolio modules
make test         # full pytest suite
make principles-test
```

Direct pytest examples:

```powershell
pytest -q tests/test_policy_safety_contract.py
pytest -q tests/test_proxy_drift_toolkit.py --basetemp=.pytest_tmp
pytest -q --junitxml=reports/junit.xml
```

`pytest.ini` sets `--import-mode=importlib` and `--basetemp=.pytest_tmp` so temp dirs stay under the repo (avoids Windows `%TEMP%` cleanup noise and duplicate module collisions).

---

## Branch workflow

| Branch | Purpose |
|--------|---------|
| `Multi_Domain_Decision_Platform` | Current default development branch — merge via PR only |
| `main` / `master` | Protected alternate / legacy default branches — merge via PR only |
| `feature/*`, `fix/*`, `chore/*` | Short-lived work branches |
| `chore/setup-ci-cd` | Example CI setup branch |

Recommended flow:

1. `git checkout -b feature/my-change`
2. Implement + run local checks (`make lint`, `make test`)
3. Open PR → **CI** workflow runs automatically
4. Squash merge after review + green checks

Do **not** push secrets, `.env`, tokens, or local audit exports.

---

## Pull request workflow

On every **pull request to `Multi_Domain_Decision_Platform`, `main`, or `master`**, GitHub Actions runs [`.github/workflows/ci.yml`](../.github/workflows/ci.yml):

| Job | What it checks |
|-----|----------------|
| `lint` | Ruff lint + format, Bandit on core packages |
| `typecheck` | Mypy on `src/platform_core/{ai_risk_analyst,risk,governance,analytics}` |
| `test` | Safety contracts (ordered), full pytest, Linux integration, principle tests, fixture CLI smoke |
| `test-windows` | Full pytest on Windows — **fails if any test is skipped** |
| `build-smoke` | `docker compose config`, Docker image build, compose health contracts |
| `frontend-build` | `npm ci` + `npm run build` |

Artifacts: JUnit XML (`junit-<sha>`) retained 14 days.

### Related workflows (not duplicated in CI)

| Workflow | When | Purpose |
|----------|------|---------|
| [`build.yml`](../.github/workflows/build.yml) | Push to default branch | Build + push immutable image to **GHCR** |
| [`deploy.yml`](../.github/workflows/deploy.yml) | After successful Build (main) or manual | SSH deploy to VM via Docker Compose |
| [`security.yml`](../.github/workflows/security.yml) | PR/push + weekly schedule | pip-audit, Trivy filesystem + container |

Legacy [`lint.yml`](../.github/workflows/lint.yml) and [`test.yml`](../.github/workflows/test.yml) are **manual-only** (coverage debugging).

---

## Recommended branch protection (`main`)

GitHub → **Settings → Branches → Branch protection rules**

### Required status checks

Enable **Require status checks to pass before merging** and select:

- `lint`
- `typecheck`
- `test`
- `test-windows`
- `build-smoke`
- `frontend-build`

Optional (stricter): `pip-audit`, `trivy (filesystem)`, `trivy (container)` from **Security** workflow.

### Review policy

| Setting | Recommendation |
|---------|----------------|
| Require pull request before merging | On |
| Required approving reviews | 1 |
| Dismiss stale approvals on new commits | On |
| Require conversation resolution | On |
| Allow force pushes | **Off** |
| Include administrators | On (production repos) |

See also: [ci_branch_protection.md](ci_branch_protection.md)

---

## Deployment strategy

### Target architecture

This project deploys as a **Docker Compose stack** on a Linux VM (or similar host):

- **API** — FastAPI (`Dockerfile` → GHCR)
- **Postgres + Redis** — `docker-compose.yml`
- **Prometheus + Grafana** — optional monitoring compose files
- **Frontend** — Next.js (build separately; serve via your chosen host or container)

There is **no Vercel/Netlify/Railway config** in-repo; production path is **GHCR + SSH + compose**.

### CI → CD pipeline

```text
PR merge to main
  → CI (ci.yml) must be green
  → Build (build.yml) pushes ghcr.io/<org>/<repo>:<full-sha>
  → Deploy (deploy.yml) SSHs to VM, docker compose pull/up, curls /platform/ready
```

**Never deploy `:latest` in production** — use immutable `IMAGE_TAG=<full-git-sha>`.

### GitHub secrets (configure in repo Settings → Secrets)

Deploy workflow expects (no defaults in repo):

| Secret | Purpose |
|--------|---------|
| `DEPLOY_HOST` | Target VM hostname or IP |
| `DEPLOY_USER` | SSH user |
| `DEPLOY_SSH_KEY` | Private key for deploy user |
| `DEPLOY_PATH` | Remote directory containing compose files |

Runtime env vars (set on the **host** or in compose `.env` — **not committed**):

| Variable | Example use |
|----------|-------------|
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | Database |
| `DATABASE_URL` | API connection string |
| `PLATFORM_API_TOKEN` / `X-Api-Token` | API auth |
| `DEMO_MODE` | `true` for fixture-only demo stack |
| `NEXT_PUBLIC_PLATFORM_API` | Frontend build-time API URL |

Local demo without secrets:

```powershell
docker compose -f docker-compose.demo.yml up --build
make demo-up
```

### Rollback

Manual deploy with prior SHA:

GitHub Actions → **Deploy** → **Run workflow** → set `image_tag` to the previous commit SHA.

---

## Environment variables and secrets

| Do | Don't |
|----|-------|
| Store secrets in GitHub Actions secrets or host `.env` | Commit `.env`, API keys, SSH keys |
| Use fixture mode in CI (`--fixture`, `DEMO_MODE=true`) | Point CI at production databases |
| Document required vars in compose comments / this doc | Hard-code tokens in workflows |

CI sets only non-secret env:

- `PYTHONPATH=${{ github.workspace }}`
- `NEXT_PUBLIC_PLATFORM_API=http://127.0.0.1:8000` (frontend build stub)

---

## Epistemic / safety note

CI validates **contracts** (dry-run defaults, policy tests, replay determinism). Passing CI does **not** prove production safety on live Windows endpoints — observation ≠ proof, policy ALLOW ≠ autonomous repair approval.
