# Windows Network Recovery Toolkit (minimal)

Local-first **probe → feature → decision → actions → audit**. The Python layer only **recommends**
`scripts/*.bat` paths; it never runs them.

## Flow (under 5 minutes)

1. **`core/probes.py`** — Windows read-only checks (ping, nslookup, TCP/443, `curl` HTTPS, HKCU/WinHTTP proxy, adapters, gateway, socket counts).
2. **`core/features.py`** — Typed feature dict passed to rules.
3. **`core/decision.py`** — Single file of **if/else** confidence bumps (same heuristics as the former `src.decision_engine.scoring`).
4. **`core/actions.py`** — Maps primary issue → `{ title, detail, script?, risk }` rows (no subprocess).
5. **`audit.py`** — Append `logs/decision_audit.jsonl`, overwrite `reports/last_diagnosis.json`.
6. **`agent.py`** — Optional loop; prints JSON + suggestions only.

## Run

```powershell
# From repo root (Windows; needs ping/nslookup/PowerShell curl in PATH)
python agent.py

# Fixture (no probes)
python agent.py --fixture path\to\fixture.json

python -m core   # same routing as agent.py
```

Repeated sampling:

```powershell
python agent.py --interval 60
```

## Safety

- No automatic repair: open **File Explorer** → `scripts\` and run batches **yourself** after reading the titles in the console output.
- High-risk scripts (e.g. `reset_firewall.bat`, `one_click_fix.bat`) appear only as labeled suggestions.

## Tests

```powershell
pip install -r requirements.txt
pytest -q
```

## Repo hygiene

Use `python tools/repo_size_audit.py` and `python tools/cleanup_generated.py` (dry-run) to prune `node_modules`, `.venv`, logs, etc.—see script headers.

## Removed in this simplification

Legacy `src/`, FastAPI `backend/`, Next `frontend/`, `platform_core/`, `endpoint_agent/`, `failure_system/`,
`auto_remediation/`, duplicate `agent/`, `network_agent/`, `hybrid_frontend/`, `evidence/`, sprawling `docs/`, and
prior test matrix—replaced by the `core/` package + `agent.py` + focused tests.
