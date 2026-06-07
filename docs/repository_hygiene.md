# Repository hygiene

Keep the git tree focused on **source, fixtures, and docs**. Runtime artifacts stay local.

---

## Ignored paths (`.gitignore`)

| Path | Reason |
|------|--------|
| `node_modules/`, `.next/` | Frontend build deps |
| `.venv/`, `__pycache__/`, `*.egg-info/` | Python env / packaging |
| `logs/`, `reports/` | Operator runtime output |
| `platform_data/` | Platform JSONL store |
| `*.jsonl`, `*.log`, `*.sqlite`, `*.zip` | Local audit / DB / bundles |

Placeholders: `logs/.gitignore`, `reports/.gitignore` keep directories without committing content.

---

## Tools

```powershell
# Preview largest files (excludes common generated dirs)
python tools/repo_size_audit.py

# Preview cleanup (dry-run default)
python tools/cleanup_generated.py

# Delete generated dirs
python tools/cleanup_generated.py --apply
```

---

## Before committing

1. Run `python tools/cleanup_generated.py` and ensure no accidental `*.jsonl` in `git status`.
2. Do not commit `.venv/`, `node_modules/`, or egg-info directories.
3. Prefer `demo_data/manifest.json` + `tests/fixtures/` over copying machine snapshots into the repo.

---

## CI expectations

GitHub Actions runs on Ubuntu with `pip install -e ".[dev]"` — no Windows probes, no destructive `.bat` scripts.

See [.github/workflows/ci.yml](../.github/workflows/ci.yml).
