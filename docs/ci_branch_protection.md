# CI/CD branch protection

This repository uses GitHub Actions workflows under [`.github/workflows/`](../.github/workflows/):

| Workflow | File | Purpose |
|----------|------|---------|
| **CI (primary)** | `ci.yml` | `lint` · `test` · `build-smoke` · `frontend-build` |
| **Lint (legacy)** | `lint.yml` | Ruff + Black — overlaps `ci` job `lint` |
| **Test (extended)** | `test.yml` | mypy, coverage pytest, safety regression — overlaps `ci` job `test` |
| **Build (release)** | `build.yml` | Docker image push to GHCR on default branch |
| **Security** | `security.yml` | pip-audit, Trivy (filesystem + container) |

Gap audit: [platform_engineering_gap_report.md](platform_engineering_gap_report.md)

Artifacts (JUnit XML, coverage XML/HTML, SARIF, pip-audit JSON) are uploaded per workflow run and retained 7–30 days.

---

## Recommended branch protection ( `main` / `master` )

Configure in **GitHub → Settings → Branches → Branch protection rules**.

### Required status checks

Enable **Require status checks to pass before merging** and select:

| Check name (job) | Workflow | Rationale |
|------------------|----------|-----------|
| `lint` | CI | Ruff on first-party Python |
| `test` | CI | Safety contracts, full pytest, fixture CLI smoke, health contracts |
| `build-smoke` | CI | `docker compose config`, image build, compose/health tests |
| `frontend-build` | CI | Next.js dashboard compiles |
| `pip-audit` | Security | Python dependency CVEs |
| `trivy (filesystem)` | Security | Repo secrets/misconfig/high vulns |
| `trivy (container)` | Security | Production image scan |
| `docker` | Build (optional) | GHCR push on merge to default branch |
| `mypy` | Test (optional) | Extended typing gate |

Optional (stricter teams): require **all** workflows on `schedule` security runs to stay green weekly.

### Review policy

| Setting | Recommendation |
|---------|----------------|
| **Require a pull request before merging** | Enabled |
| **Required approving reviews** | **1** (2 for production release branches) |
| **Dismiss stale pull request approvals when new commits are pushed** | Enabled |
| **Require review from Code Owners** | Enabled when `CODEOWNERS` exists |
| **Require conversation resolution before merging** | Enabled |
| **Require linear history** | Optional (squash merge preferred) |
| **Include administrators** | Enabled in production repos |
| **Restrict who can push to matching branches** | Release managers / bots only |
| **Allow force pushes** | **Disabled** |
| **Allow deletions** | **Disabled** |

### Merge strategy

- **Squash merge** for feature branches (clean history, one commit per PR).
- **Merge commit** only for release tags if you cut semver from `main`.

---

## Docker tags

On push to the **default branch** (`build.yml`):

| Tag | Example |
|-----|---------|
| `latest` | `ghcr.io/<org>/<repo>:latest` |
| Commit SHA | `ghcr.io/<org>/<repo>:<full-sha>` |

Pull requests **build** the image but do **not** push to GHCR (tarball artifact only).

---

## Local parity

```bash
pip install -e ".[dev]"
ruff check platform_core backend evidence failure_system telemetry tests
ruff format --check platform_core backend evidence failure_system telemetry tests
black --check platform_core backend evidence failure_system telemetry tests
mypy
pytest --cov=platform_core --cov=backend --cov-report=term-missing
pip-audit
docker build -t er-platform-api:local .
```

---

## Epistemic / safety note

CI validates **contracts** (dry-run defaults, policy tests, replay determinism). Passing CI does **not** prove production safety on live endpoints — **observation ≠ proof**, **policy ALLOW ≠ autonomous repair approval**.
