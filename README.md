# Endpoint Reliability Platform (Windows Network Recovery Toolkit)

> A **local-first Windows diagnostics and remediation-preview platform** that turns proxy, DNS, browser, and network failures into explainable events, policy-gated actions, and auditable dashboard insights.

This repo keeps **beginner batch workflows** intact while layering **structured diagnostics**, **append-only evidence**, and an optional **FastAPI + Next.js** stack so you can show **what broke**, **what policy allows**, and **what was audited**—before any repair runs.

---

## Problem

Windows often looks “online” while **browser or dev-tool traffic fails**—typically around **DNS**, **WinINET/WinHTTP proxy drift**, **TLS path**, or **browser-only** behavior. Flat repair scripts can change network state without enough context. Here, **diagnosis, hypotheses, policy evaluation, preview, and audit** come first; remediation is **explicit**, **allowlisted**, and **logged** where implemented.

---

## Beyond `scripts/*.bat`

The beginner toolkit under [`scripts/`](scripts/) remains **unchanged** in layout and intent: familiar `.bat` flows for operators who want guided steps.

The Python layers add:

- **`python -m src`** — explainable CLI: proxy guard, network-state snapshots, deterministic decision engine, repair-safe low-risk paths (see [`docs/cli_reference.md`](docs/cli_reference.md)).
- **`failure_system/`** — Failure Knowledge System: safe probes → **FailureBlock** records in **append-only JSONL** (optional HTTP API mirrors CLI semantics; no auto-repair).
- **`platform_core/`** + **`backend/`** — typed models, append-only `platform_data/*.jsonl`, policy gates, **FastAPI** routes under **`/platform/*`**.
- **`frontend/`** — Next.js dashboard at **`/platform`** (points at `NEXT_PUBLIC_PLATFORM_API`).
- **`endpoint_agent/`** — **observe-only** local cycles; optional POST to your backend when configured (no auto-repair from the agent module).

---

## Core features

| Track | What it is |
| --- | --- |
| **`scripts/*.bat`** | Beginner Windows batch toolkit (unchanged). See [`docs/script_reference.md`](docs/script_reference.md). |
| **`python -m src`** | Explainable diagnostics CLI: proxy guard, network-state snapshots, decision engine, repair-safe low-risk batch path. |
| **`failure_system/`** | Failure Knowledge System: probes → **FailureBlock** + append-only JSONL ([`failure_system`](failure_system/)). |
| **Platform stack** | Append-only **`platform_data/*.jsonl`**, **`/platform/*`** ingest + reads, metrics, incidents, attribution, RBAC-shaped headers, **`frontend/`** dashboard. |

Full command matrix: [`docs/cli_reference.md`](docs/cli_reference.md).

---

## Safety model

| Constraint | What it means in this repo |
| --- | --- |
| **Diagnose first** | Collectors and APIs surface evidence before repair-oriented paths. |
| **Preview before repair** | CLI and **`POST /platform/remediation/preview`** describe intended actions. |
| **Dry-run default** | **`POST /platform/remediation/execute`** defaults to **`dry_run=true`** in the request model. |
| **Allowlist-only remediation** | Executable remediation resolves through the platform registry and policy gates—not arbitrary strings. |
| **No arbitrary shell from API** | Platform routes do not accept free-form shell; **`/api/*`** toolkit bridges invoke fixed **`python -m src …`** argv (see [`backend/live_observability.py`](backend/live_observability.py)). |
| **No default log uploads** | JSONL and logs stay **local** unless you explicitly point agents or tools at a backend. |
| **High-risk actions blocked** | Firewall reset, adapter disable, and similar paths stay **off** API execution unless modeled as preview/manual-only (see tests under [`tests/`](tests/)). |
| **Heuristic attribution ≠ proof** | Process correlation and evidence tiers are **hypotheses**, not proof of who wrote a registry value—see [`evidence/`](evidence/) and [`docs/evidence_pipeline.md`](docs/evidence_pipeline.md). |

More detail: [`docs/safety_model.md`](docs/safety_model.md), [`SECURITY.md`](SECURITY.md).

---

## Architecture

End-to-end mental model:

**collect → snapshot → detect drift → attribute → decide policy → preview remediation → audit → dashboard**

| Stage | Role |
| --- | --- |
| **Collect** | Safe probes via **`python -m src`**, **`failure_system`**, or **`endpoint_agent`** cycles (observe-only; no repair from the agent module). |
| **Snapshot** | Persist endpoint/network snapshots as JSONL under **`platform_data/`** (or paths set by **`PLATFORM_DATA_DIR`**). |
| **Detect drift** | Compare snapshots / baselines for proxy, DNS, and related divergence. |
| **Attribute** | Merge listener inventory with optional Procmon/Sysmon-style evidence—**ranked hypotheses**, not forensic proof. |
| **Decide policy** | Allowlists, risk tiers, RBAC headers, and **`platform_core`** policy evaluation before execution. |
| **Preview remediation** | **`/platform/remediation/preview`** and CLI previews; blocked actions remain blocked. |
| **Audit** | Append audit rows to JSONL / **`logs/`** for previews and allowlisted execution attempts. |
| **Dashboard** | **`frontend/`** Next.js app under **`/platform`** for health, metrics, events, incidents. |

Diagrams and depth: [`docs/architecture_platform.md`](docs/architecture_platform.md), [`docs/platform_architecture.md`](docs/platform_architecture.md).

Contracts: `platform_core/platform_event_contract.py`, `platform_core/policy_engine.py`, `config/platform_policy.example.json`.

---

## Repository layout

| Path | Role |
| --- | --- |
| `scripts/` | Beginner Windows **`.bat`** toolkit (unchanged) |
| `src/` | **`python -m src`** — explainable CLI, proxy guard, decision pipeline |
| `failure_system/` | **FailureBlocks** and append-only JSONL |
| `platform_core/` | Platform models, policy, append-only storage, metrics, incidents |
| `endpoint_agent/` | **Observe-only** endpoint cycles; ingest client (optional HTTP) |
| `backend/` | **FastAPI** — **`/platform/*`** plus SaaS-demo and **`/api/*`** toolkit bridges ([`backend/main.py`](backend/main.py)) |
| `frontend/` | **Next.js** dashboard (**`/platform`**) |
| `evidence/` | Conservative attribution / evidence adapters (Procmon, Sysmon, ETW-style facades) |
| `tests/` | Offline regression and safety tests |

Do **not** commit real **`logs/`**, **`platform_data/`**, or operator-owned machine data.

---

## 3-minute demo

From the **repository root** in **PowerShell**. Installs match [`docs/demo_script.md`](docs/demo_script.md).

**Dependencies**

```powershell
pip install -r failure_system/requirements.txt
pip install -r requirements-platform.txt
```

**Seed demo JSONL (optional)**

```powershell
python -m platform_core.demo_fleet --data-dir platform_data_fleet_demo --reset
```

**Point the backend at that directory**

```powershell
$env:PLATFORM_DATA_DIR = "$(Get-Location)\platform_data_fleet_demo"
$env:PYTHONPATH = (Get-Location).Path
uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

**Smoke the API** (browser or `curl`):

- `GET http://127.0.0.1:8000/platform/health`
- `GET http://127.0.0.1:8000/platform/metrics`

**Optional: Next.js dashboard**

```powershell
cd frontend
copy .env.local.example .env.local
```

Edit `.env.local` so `NEXT_PUBLIC_PLATFORM_API=http://127.0.0.1:8000`, then:

```powershell
npm install
npm run dev
```

Open the app URL printed by Next.js (commonly `http://localhost:3000`) and navigate to **`/platform`**.

Longer narrative: [`docs/demo_script.md`](docs/demo_script.md).

---

## Quick starts

### Beginner scripts

```powershell
cd <repo-root>\scripts
# e.g. auto_diagnose.bat — read-oriented; repairs use explicit prompts where implemented
```

### `python -m src`

```powershell
cd <repo-root>
python -m src diagnose
```

### Failure Knowledge System

```powershell
pip install -r failure_system\requirements.txt
python -m failure_system diagnose
```

### Backend + observe-only agent

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

## HTTP surface

Routes below are defined in [`backend/platform_routes.py`](backend/platform_routes.py) (router prefix **`/platform`**). The same app may expose SaaS-style routes on **`backend.main`** (e.g. `/diagnose`, billing); see source for the full list.

### `/platform/*` (platform prototype)

| Method | Path | Notes |
| --- | --- | --- |
| GET | `/platform/health` | Build metadata + data dir |
| POST | `/platform/agent/heartbeat` | Heartbeat ingest |
| POST | `/platform/ingest/heartbeat` | Alias of heartbeat |
| POST | `/platform/snapshots` | Snapshot ingest |
| POST | `/platform/ingest/snapshot` | Alias of snapshots |
| GET | `/platform/endpoints` | List endpoints |
| GET | `/platform/endpoints/{endpoint_id}` | Endpoint detail |
| GET | `/platform/failure-events` | List failure events |
| POST | `/platform/failure-events/ingest` | Ingest failure event |
| POST | `/platform/ingest/failure-event` | Alias of failure-events ingest |
| GET | `/platform/failure-events/{event_id}` | Get failure event |
| POST | `/platform/remediation/preview` | Policy preview |
| POST | `/platform/remediation/execute` | Execute path; request defaults **`dry_run=True`** |
| GET | `/platform/audit` | Audit rows (RBAC gated) |
| GET | `/platform/metrics` | JSONL-derived KPIs |
| GET | `/platform/events` | Normalized envelopes |
| GET | `/platform/incidents` | Deterministic clusters |
| GET | `/platform/attribution/{event_id}` | Evidence fusion |
| GET | `/platform/policy/summary` | Policy summary |
| POST | `/platform/replay/preview` | Replay preview |

Contract and headers: [`docs/platform_api_contract.md`](docs/platform_api_contract.md).

### `/api/*` (JWT toolkit bridges)

[`backend/live_observability.py`](backend/live_observability.py) exposes read-mostly **`python -m src`** wrappers, e.g. **`GET /api/proxy/status`**, **`GET /api/proxy/owner`**, **`POST /api/proxy/disable-preview`**, **`POST /api/proxy/disable`** (typed confirmation phrase), **`GET /api/snapshot`**, **`POST /api/diagnose-live`**, **`GET /api/reports/latest`**. Requires authenticated user dependency—see module docstrings.

---

## Interview pitch

**One-liner:** *“I built a local-first Windows endpoint-reliability prototype: append-only JSONL, policy-gated remediation previews with dry-run defaults, honest attribution tiers, and a Next dashboard—without throwing away beginner `.bat` workflows.”*

**STAR anchor:** Situation (browser fails while “online”) → Task (structure + safety) → Action (`failure_system` + `python -m src` + `platform_core` + `/platform/*`) → Result (auditable pipeline, tests block high-risk API execution). Full write-up: [`docs/interview_case_study.md`](docs/interview_case_study.md).

**Talking points for platform / SRE interviews:**

- **Local-first evidence** — FailureBlocks and platform JSONL are operator-owned artifacts, not silent telemetry uploads.
- **Policy before subprocess** — previews and allowlists mirror how you’d gate change management in production.
- **Honest limits** — regression tests and docs state what attribution can and cannot prove.

---

## Tests & CI

```powershell
$env:PYTHONPATH = (Get-Location).Path
pytest -q
```

[`.github/workflows/ci.yml`](.github/workflows/ci.yml) runs **`pytest` only**—not Windows repair scripts.

Strategy: [`docs/test_strategy.md`](docs/test_strategy.md).

---

## Repository hygiene

Huge working trees usually mean **`node_modules`**, **`.venv`**, **`.next`**, **logs/reports JSONL**, and similar—not authored source. See **[`docs/repository_hygiene.md`](docs/repository_hygiene.md)** and run `python tools/repo_size_audit.py --top 30` before `python tools/cleanup_generated.py` (dry-run by default).

---

## License

MIT — see [LICENSE](LICENSE).

