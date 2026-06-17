# Production deployment (Docker Compose + GitHub Actions CD)

See also [architecture_service.md](architecture_service.md) for diagrams and module map.

**CI/CD:** `Build` workflow pushes immutable images to GHCR; `Deploy` workflow rolls out to a VM via SSH using `IMAGE_TAG=<full-git-sha>` (never `:latest`).

---

## Prerequisites

- Docker Engine 24+ and Docker Compose v2 on the deploy host
- GitHub repository with `Build` and `Deploy` workflows enabled
- For private GHCR packages: `docker login ghcr.io` on the server (see [GHCR login](#ghcr-login-on-the-server))

---

## Local development (unchanged)

Build from source — no `IMAGE_TAG` required:

```bash
cp .env.example .env
docker compose up --build
```

| Service | URL | Notes |
|---------|-----|-------|
| API + OpenAPI | http://localhost:8000/docs | Bearer or `X-Operator-*` headers |
| Liveness | http://localhost:8000/platform/health | Docker HEALTHCHECK target |
| Readiness | http://localhost:8000/platform/ready | Fails 503 until startup checks pass |
| Prometheus | http://localhost:9090 | Scrapes `GET /metrics` |
| Grafana | http://localhost:3001 | Default `admin` / `$GRAFANA_ADMIN_PASSWORD` |

---

## Production VM deployment (immutable image)

### Compose files

| File | Purpose |
|------|---------|
| `docker-compose.yml` | Base stack (Postgres, API build, Prometheus, Grafana) |
| `docker-compose.prod.yml` | **CD overlay** — API pulls `ghcr.io/<owner>/<repo>:${IMAGE_TAG}` |

Required environment variables for production pull:

| Variable | Example | Purpose |
|----------|---------|---------|
| `IMAGE_TAG` | `719b36a1b2c3...` (40-char SHA) | Immutable deploy tag — **never `latest`** |
| `GHCR_IMAGE` | `ghcr.io/kozphy/windows-network-recovery-toolkit` | Lowercase GHCR repository path |

Add to server `.env` (optional defaults):

```bash
GHCR_IMAGE=ghcr.io/kozphy/windows-network-recovery-toolkit
# IMAGE_TAG is set per deploy by CI or operator
```

### Manual deploy on server

```bash
cd /opt/windows-network-recovery-toolkit   # or your DEPLOY_PATH
git pull   # compose files + configs only; API image comes from GHCR

export IMAGE_TAG=<full-git-sha>
export GHCR_IMAGE=ghcr.io/kozphy/windows-network-recovery-toolkit

./scripts/deploy-compose-prod.sh
```

Or without the script:

```bash
export IMAGE_TAG=<full-git-sha> GHCR_IMAGE=ghcr.io/kozphy/windows-network-recovery-toolkit
docker compose -f docker-compose.yml -f docker-compose.prod.yml pull api
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --no-build
curl -fsS http://localhost:8000/platform/ready
```

### Rollback to a previous SHA

```bash
export IMAGE_TAG=<previous-commit-sha>
export GHCR_IMAGE=ghcr.io/kozphy/windows-network-recovery-toolkit
./scripts/deploy-compose-prod.sh
```

Or trigger **Actions → Deploy → Run workflow** and set `image_tag` to the previous SHA.

---

## Server setup (one-time)

1. **Provision a Linux VM** (Ubuntu 22.04+ recommended) with Docker and Compose v2.
2. **Clone the repository** to `DEPLOY_PATH` (e.g. `/opt/windows-network-recovery-toolkit`).
3. **Configure `.env`** from `.env.example`:
   - Set `PLATFORM_API_KEY` (required before non-local exposure)
   - Set `GRAFANA_ADMIN_PASSWORD`
   - Set Postgres credentials if not using defaults
4. **GHCR login** (if package is private):

```bash
echo "$GHCR_PAT" | docker login ghcr.io -u YOUR_GITHUB_USER --password-stdin
```

Use a fine-scoped PAT with `read:packages`. Store credentials in root's docker config or a CI-managed secret on the server.

5. **Authorize deploy SSH key** — add the public half of `DEPLOY_SSH_KEY` to `~/.ssh/authorized_keys` for `DEPLOY_USER`.

6. **First boot** (optional local build, or deploy a known SHA from GHCR):

```bash
export IMAGE_TAG=<sha-from-main> GHCR_IMAGE=ghcr.io/kozphy/windows-network-recovery-toolkit
./scripts/deploy-compose-prod.sh
```

---

## GitHub Actions CD

### Workflows

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| **Build** | Push/PR to `main`, `master`, `amd_version`, `feature/**`, `fix/**`, `ci/**` | Lint, test, build; push `ghcr.io/<owner>/<repo>:<SHA>` on non-PR |
| **Deploy** | After successful **Build** on `main`/`master`/`amd_version`, or `workflow_dispatch` | SSH deploy with immutable `IMAGE_TAG` |

**Safety:** Deploy does **not** run for pull requests. Auto-deploy only follows successful builds on default branches.

### Required GitHub secrets

Configure in **Settings → Secrets and variables → Actions**:

| Secret | Description |
|--------|-------------|
| `DEPLOY_HOST` | VM hostname or IP |
| `DEPLOY_USER` | SSH user (e.g. `deploy`) |
| `DEPLOY_SSH_KEY` | Private key (PEM) for SSH — never logged |
| `DEPLOY_PATH` | Absolute path to repo on server (e.g. `/opt/windows-network-recovery-toolkit`) |

Optional: configure **Environment `production`** with required reviewers for deploy approval.

### GHCR image tags

On every non-PR push, **Build** publishes:

```text
ghcr.io/<owner>/<repo>:<full-github-sha>
```

`latest` may be updated on the default branch for convenience, but **CD always deploys the SHA tag**.

Verify an image exists:

```bash
docker pull ghcr.io/kozphy/windows-network-recovery-toolkit:<sha>
```

### Deploy audit log (workflow)

Each deploy logs (no secrets):

- `deployed_image` — full image reference
- `commit_sha` — same as `IMAGE_TAG`
- `deployment_time` — UTC timestamp
- `health_check` — result of `GET /platform/ready`

---

## Optional full stack (local / VM)

Dashboard, Loki, and Promtail:

```bash
docker compose -f docker-compose.yml -f docker-compose.full.yml up --build
```

For CD with prod overlay:

```bash
export IMAGE_TAG=<sha> GHCR_IMAGE=ghcr.io/kozphy/windows-network-recovery-toolkit
docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.full.yml up -d --no-build
```

---

## Optional Kubernetes (Helm)

Not the default CD path. When a cluster is available:

```bash
helm upgrade --install erp-platform ./deploy/helm/erp-platform \
  --namespace erp --create-namespace \
  --set image.repository=ghcr.io/kozphy/windows-network-recovery-toolkit \
  --set image.tag="${GITHUB_SHA}" \
  --set ingress.enabled=true \
  --wait --timeout 5m
```

Set `image.tag` to a **full git SHA**, not `latest`. See `deploy/helm/erp-platform/values.yaml`.

---

## Configuration reference

Validated via `platform_core.settings.PlatformSettings`:

| Variable | Default | Purpose |
|----------|---------|---------|
| `PLATFORM_SAFE_MODE` | `1` | Safety-first defaults |
| `PLATFORM_DATA_DIR` | `./platform_data` | Append-only JSONL root |
| `PLATFORM_API_KEY` | unset | Optional Bearer auth |
| `FAIL_FAST_ON_STARTUP` | `0` ( `1` in Docker ) | Exit if startup checks fail |
| `REQUIRE_PING_BINARY` | `0` ( `1` in Docker ) | Hard-fail without `ping` |
| `CORS_ALLOW_ORIGINS` | `*` | Tighten before production |

Loads from repo-root `.env` and/or `backend/.env`.

---

## Linux vs Windows agents

| Host | Diagnostics | Remediation |
|------|-------------|-------------|
| Linux / Debian / Ubuntu / WSL | `LinuxNetworkDiagnostics` (observe-only) | Not in Linux container |
| Windows endpoint | `WindowsNetworkDiagnostics` (WinINET/WinHTTP reads) | Policy-gated on agent; never automatic in API |

**Observation is not proof** — Windows proxy reads remain heuristic until Sysmon/Procmon proof tiers are attached.

---

## Safety invariants

- No auto-repair containers or cron remediation jobs
- Execute routes default to `dry_run=True`
- Append-only audit under `PLATFORM_DATA_DIR`
- Policy `ALLOW` does not bypass typed confirmation for destructive actions
- CD never deploys from untrusted PR workflows
- CD fails fast if `IMAGE_TAG` is empty or readiness check fails
