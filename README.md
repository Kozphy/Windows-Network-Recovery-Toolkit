# Endpoint Reliability Platform (Windows toolkit core)

**Local-first Windows diagnostics** with unchanged beginner `**scripts/*.bat`**, explainable `**python -m src**`, the **Failure Knowledge System** (**FailureBlocks** + JSONL), and an optional **Endpoint Reliability Platform prototype** (`**platform_core/`**, `**backend` `/platform/***`, `**endpoint_agent/**`, `**evidence/**`).

**Safety defaults:** **no silent destructive repair**, **no default log uploads**, **no arbitrary shell execution from the API**, **dry-run first** on `/platform/remediation/execute`, **allowlist-only** remediation.

---

## Problem

Windows often looks “online” while **browser or dev-tool traffic fails** because of **DNS**, **WinINET/WinHTTP proxy drift**, **TLS path**, or **browser-only** issues. Flat repair scripts can mutate state without enough evidence; this repo keeps **diagnosis, hypothesis, policy, preview, and audit** first.

---

## What you get (core features)


| Track                        | What it is                                                                                                                                    |
| ---------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| **Beginner `.bat`**          | Guided diagnose/reset scripts (unchanged layout). See `[docs/script_reference.md](docs/script_reference.md)`.                                 |
| `**python -m src**`          | Proxy guard, network-state snapshots, decision engine, repair-safe low-risk batch path.                                                       |
| **Failure Knowledge System** | Deterministic probes → **FailureBlock** JSONL (read-only APIs).                                                                               |
| **Platform prototype**       | Append-only `**platform_data/*.jsonl`**, `**/platform/ingest/***`, metrics, incidents, attribution, RBAC-lite, Next.js `/platform` dashboard. |


Full CLI tables live in `**[docs/cli_reference.md](docs/cli_reference.md)**`.

---

## 3-minute demo

1. `pip install -r failure_system/requirements.txt` and `pip install -r requirements-platform.txt`
2. `pythoㄏn -m platform_core.demo_fleet --data-dir platform_data_fleet_demo --reset`
3. `$env:PLATFORM_DATA_DIR = "$(Get-Location)\platform_data_fleet_demo"` ; `$env:PYTHONPATH = (Get-Location).Path` ; `uvicorn backend.main:app --host 127.0.0.1 --port 8000`
4. Open `**GET /platform/health**`, then `**GET /platform/metrics**`.
5. `cd frontend` → set `**NEXT_PUBLIC_PLATFORM_API=http://127.0.0.1:8000**` → `npm run dev` → visit `**/platform**`.

Step-by-step narrative: `**[docs/demo_script.md](docs/demo_script.md)**`.

---

## Architecture (platform story)

Pipeline: **collect → snapshot → detect drift → attribute → decide policy → preview remediation → audit → dashboard**.

Mermaid + file map: `**[docs/architecture_platform.md](docs/architecture_platform.md)`** (plus `[docs/platform_architecture.md](docs/platform_architecture.md)`).

Typed interview envelopes: `**platform_core/platform_event_contract.py**`. Policy verbs + optional JSON hints: `**platform_core/policy_engine.py**`, `**config/platform_policy.example.json**`.

---

## Safety model

- **Diagnose first**; **preview** before repair; **typed confirmation** where implemented.  
- **Heuristic process correlation ≠ proof** of who wrote registry values — see `**evidence/`** + `[docs/evidence_pipeline.md](docs/evidence_pipeline.md)`.  
- **High-risk** actions (firewall reset, adapter disable, arbitrary command) stay **blocked** from API execution paths except manual/blocked preview flows — see tests under `**tests/test_safety_regression.py`**, `**tests/test_api_platform_routes.py**`.  
- **Live subprocess** on execute writes `**execute_live_pending`** audit immediately before allowlisted `cmd /c` launch.  
- Logs and JSONL are **local** — do not commit real `**logs/`**, `**platform_data/**`, or operator data.

Details: `[docs/safety_model.md](docs/safety_model.md)`, `[SECURITY.md](SECURITY.md)`.

---

## Quick starts

### Beginner scripts

```powershell
cd <repo-root>\scripts
# auto_diagnose.bat — read-oriented; repairs require explicit prompts
```

### Advanced CLI (summary)

```powershell
cd <repo-root>
python -m src diagnose
```

Proxy / network-state / full command matrix: `**[docs/cli_reference.md](docs/cli_reference.md)**`.

### Failure Knowledge System

```powershell
pip install -r failure_system\requirements.txt
python -m failure_system diagnose
```

### Platform backend + agent

```powershell
pip install -r requirements-platform.txt
$env:PYTHONPATH = (Get-Location).Path
uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

```powershell
python -m endpoint_agent --once --api http://127.0.0.1:8000
python -m endpoint_agent --service --interval 30 --dry-run
```

---

## HTTP surface (high level)


| Method | Path                               | Notes                                      |
| ------ | ---------------------------------- | ------------------------------------------ |
| GET    | `/platform/health`                 | Version + safe mode                        |
| GET    | `/platform/metrics`                | JSONL-derived KPIs                         |
| GET    | `/platform/events`                 | Normalized envelopes                       |
| GET    | `/platform/incidents`              | Deterministic clusters                     |
| GET    | `/platform/attribution/{event_id}` | Evidence fusion                            |
| POST   | `/platform/ingest/heartbeat`       | Alias of `/platform/agent/heartbeat`       |
| POST   | `/platform/ingest/snapshot`        | Alias of `/platform/snapshots`             |
| POST   | `/platform/ingest/failure-event`   | Alias of `/platform/failure-events/ingest` |
| POST   | `/platform/remediation/preview`    | Policy preview                             |
| POST   | `/platform/remediation/execute`    | **Defaults `dry_run=true`**                |
| GET    | `/platform/audit`                  | Admin / security auditor                   |


Contract: `[docs/platform_api_contract.md](docs/platform_api_contract.md)`.

---

## Interview case study

STAR-form walkthrough + architecture narrative: `**[docs/interview_case_study.md](docs/interview_case_study.md)**`.

---

## Tests & CI

```powershell
$env:PYTHONPATH = (Get-Location).Path
pytest -q
```

`**.github/workflows/ci.yml**` runs **pytest only** — never Windows repair scripts.

Strategy: `[docs/test_strategy.md](docs/test_strategy.md)`.

---

## Repository layout (abbrev.)


| Path              | Role                                             |
| ----------------- | ------------------------------------------------ |
| `scripts/`        | Beginner `.bat` toolkit                          |
| `src/`            | `python -m src` + proxy guard                    |
| `failure_system/` | FailureBlocks + JSONL                            |
| `evidence/`       | Honest attribution + Procmon/Sysmon/ETW facades  |
| `platform_core/`  | Models, policy, JSONL, metrics, **demo_fleet**   |
| `endpoint_agent/` | Observe-only cycles + **ingest HTTP with retry** |
| `backend/`        | FastAPI + `/platform/`*                          |
| `frontend/`       | Next.js dashboard (`/platform`)                  |
| `tests/`          | Offline regression + safety                      |


---

## License

MIT — see `[LICENSE](LICENSE)`.