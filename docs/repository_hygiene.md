# Repository hygiene and disk footprint

## Why keep the diagnostic toolkit source checkout small?

**Source files** should stay tiny enough to audit, clone, and back up quickly. Disk growth beyond tens of megabytes usually means **dependency trees** (`node_modules`, `.venv`), **build caches** (`.next`, `dist`), **generated logs** (`*.jsonl`, `*.log`), **local datasets** (`platform_data/`), or **archives/installers**—not your hand-written probes and decision logic.

## What should be committed?

- **Authored**: `core/`, `agent.py`, `audit.py`, `scripts/`, `tests/`, `docs/`, `tools/`, `README.md`, `requirements.txt`, `CHANGELOG.md`.
- **Empty-dir placeholders**: e.g. `logs/.gitignore`, `reports/.gitignore` so Git can keep folders without tracking generated payloads.

## What should *not* be committed?

- Virtualenv / site-packages (`.venv/`, `venv/`).
- Node install trees (`node_modules/`, `.next/`, frontend build output).
- **Runtime output**: root `logs/`, `reports/`, `platform_data/`, stray `*.jsonl` / `*.log` from probes.
- Databases/archives you generated locally (`*.sqlite`, `*.zip`, `*.msi`, `*.exe` unless distributing a deliberate release artefact).

## Source repo vs release vs Docker vs local runtime

| Kind | Typical contents | Size guidance |
| --- | --- | --- |
| **Git source checkout** | Code + fixtures + curated docs | Often **~5–30 MB** (stdlib-only tooling); **~30–100 MB** still reasonable with larger tests/fixtures |
| **Release zip/installer** | Bundled binaries or signed packages | **~100–400 MB** may be acceptable |
| **Docker image** | OS + runtime layers | Often **~300 MB–1 GB** |
| **Developer machine checkout** | All of the above *plus* venv/node/cache/logs | Can reach **400 MB+**—that’s normal locally; trim with cleanup, don’t widen Git |

## Scripts

Audit (find what grew):

```powershell
python tools/repo_size_audit.py --top 30
python tools/repo_size_audit.py --top 30 --json
python tools/repo_size_audit.py --include-git
```

Dry-run cleanup (recommended first):

```powershell
python tools/cleanup_generated.py
python tools/cleanup_generated.py --verbose
```

Apply (⚠ destroys candidates after you type **yes**, or pass `--yes` for automation):

```powershell
python tools/cleanup_generated.py --apply
```

## Stop tracking generated paths that were accidentally committed

```powershell
git rm -r --cached node_modules .venv venv .next dist build logs reports platform_data evidence
git add .gitignore docs/repository_hygiene.md tools/
git commit -m "chore: add repository cleanup and hygiene tooling"
```

On Windows, omit paths that don’t exist. Then run **`python tools/cleanup_generated.py --apply`** locally to delete working-copy junk (after dry-run review). Verify with **`git status`**.

## Risky assumptions

- **`build/` / `dist/`**: treated as disposable. Rename authored folders that collide.
- **`logs/`**: cleanup removes root `logs/` *contents* via directory rule—archive anything forensic before **`--apply`**.
- **`core/`/`src/`/`scripts/` fixtures**: explicitly protected from broad glob deletes (`tests/` is never purged).
