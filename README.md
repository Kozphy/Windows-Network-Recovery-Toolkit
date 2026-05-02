# Windows Network Recovery Toolkit

**Local-first Windows network diagnostics** with a beginner **`.bat` toolkit**, an advanced **`python -m src` decision CLI**, the **Failure Knowledge System** (**FailureBlocks** + JSONL), and an optional **Endpoint Reliability Platform** layer (`platform_core/`, **`python -m endpoint_agent`**, **`/platform/*` API**) for portfolio-style observability—**still no silent destructive repair** and **no default log uploads**.

---

## Quick start — beginner (.bat toolkit)

Untouched scripted path for real machines:

```powershell
cd <repo-root>\scripts
# Read-oriented: auto_diagnose.bat — follow prompts; elevated admin only when a script demands it.
# Repairs: guided scripts — never silent firewall reset / adapter disable from these defaults.
```

See **`docs/script_reference.md`** for script purposes and risk notes.

### Proxy Guard Module (batch + PowerShell, no extra deps)

Stops **stale or malicious proxy settings** from breaking **Cursor, Git, npm, pip, browsers, and AI tooling** (especially when `ProxyServer` still points at **127.0.0.1:port** with nothing listening).

**Recommended workflow:** **Diagnose → Monitor (optional) → Reset (if needed) → Safe Cursor launcher.**

| Step | Script | Purpose |
| --- | --- | --- |
| 1 | `scripts\proxy_guard\diagnose_proxy.bat` | Read-only: HKCU WinINET, `netsh winhttp`, Git/npm, user `HTTP(S)_PROXY` → `reports\proxy_guard_report.txt` |
| 2 | `scripts\proxy_guard\monitor_proxy.ps1` | Poll every 5s; log proxy key changes + recent process **names** to `reports\proxy_guard_watch.jsonl` (optional `-AutoReset` — see script warning) |
| 3 | `scripts\proxy_guard\reset_proxy_safe.bat` | After you type **`YES`**: clear HKCU proxy, reset WinHTTP, unset Git/npm; optional **`CLEAR`** for user env; optional **`ADVANCED`** for machine env (rare) → `reports\proxy_guard_actions.jsonl` |
| 4 | `scripts\proxy_guard\start_cursor_safe.bat` | Runs diagnose; warns on suspicious loopback proxy; optional guided reset; launches **Cursor.exe** from common paths |

Full concepts (layers, risks, rollback): **`docs/proxy_guard.md`**.

**Troubleshooting quick hits**

| Symptom | Check |
| --- | --- |
| Cursor AI / extensions flaky while browser OK | Run **`diagnose_proxy.bat`** — HKCU `ProxyEnable` + loopback `ProxyServer`; then **`reset_proxy_safe.bat`** if appropriate |
| `git fetch` / GitHub HTTPS failures | Git global `http.proxy` / `https.proxy`; user **`HTTPS_PROXY`** env |
| `npm ERR` network / registry timeouts | `npm config get proxy`; **`HTTP_PROXY`** / **`HTTPS_PROXY`** |
| pip install failures behind corp | Same env vars + WinINET; verify **`NO_PROXY`** for internal indexes if documented |

---

## Advanced CLI — decision engine (`python -m src`)

Stdlib-first probes, **`FeatureVector`**, scored causes, **`reports/`** + **`logs/*.jsonl`**, **`repair-safe`** with typed confirmation for the first **LOW**-risk **`scripts/*.bat`** only:

```powershell
cd <repo-root>
python -m src diagnose
python -m src explain
python -m src recommend
```

Proxy observability:

```powershell
python -m src proxy-status
python -m src proxy-monitor
python -m src proxy-guard --interval 5
python -m src proxy-guard --interval 5 --auto-rollback --trust-current # optional LKG + live restore
```

`proxy-guard` follows **detect → best-effort attribute → decide (default deny) → optional rollback preview/apply → audit** (`logs/proxy_guard_pipeline_audit.jsonl` schema_version `1` plus legacy v2 sinks). On each registry change it attaches a **heuristic** `candidate_actor` (when optional **`pip install psutil`** is available)—**not proof** of the writer process; see **`docs/proxy_guard.md` § Process attribution**. Rollback restores the **prior poll’s** HKCU WinINET snapshot (never arbitrary shell commands). Typical flags:

- `python -m src proxy-guard --interval 5` — detect + stdout / control JSONL  
- `--dry-run` / `--dry-run-rollback` — no live `reg` / `netsh` restores  
- `--auto-rollback` — legacy toggle; live restore without extra phrase  
- `--rollback` — rollback path (`--rollback-confirm RESTORE_PROXY` needed for live `reg` restores unless `--auto-rollback` is also set)  

Consolidated rows also mirror to `reports/proxy_guard_watch.jsonl`, `reports/proxy_guard_actions.jsonl`,
and `logs/proxy_guard_audit.jsonl`; policy defaults prefer **`config/proxy_guard_policy.json`**. See **`docs/proxy_guard.md`**, **`docs/proxy_guard_attribution.md`** / **`docs/proxy_guard_rollback.md`**.

Docs: **`docs/architecture.md`**, **`docs/proxy_guard.md`**, **`docs/decision_engine_v2.md`**.

---

## Failure Knowledge System mode (`failure_system/`)

Deterministic probes → **`RuleEngine`** → typed **`FailureBlock`** → append-only JSONL (`data/failure_blocks/`). **Search** and **`recommend` output text/JSON only** — **no repair execution** from FKS APIs.

```powershell
cd <repo-root>
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r failure_system\requirements.txt

python -m failure_system diagnose
python -m failure_system search "dns"
python -m failure_system recommend --query "browser"

uvicorn failure_system.api:app --host 127.0.0.1 --port 8010
```

Optional: **`FAILURE_SYSTEM_DATA_DIR`** (absolute JSONL root).

Contract: **`docs/failure_block_contract.md`**.

---

## Endpoint Reliability Platform mode (optional prototype)

Structured **privacy-aware** domain model (`platform_core/`), append-only **`platform_data/*.jsonl`**, **`POST /platform/*`** on the **`backend`** app, and a local **agent** that **collects** and **never auto-repairs**.

### Architecture pointers

| Doc | Topic |
| --- | --- |
| **`docs/endpoint_reliability_platform.md`** | Vision — toolkit vs platform |
| **`docs/platform_architecture.md`** | Mermaid diagram (agent → audit) |
| **`docs/safety_and_privacy.md`** | Allowed / forbidden fields |
| **`docs/fleet_architecture.md`** | Optional future fleet pattern |
| **`docs/demo_walkthrough.md`** | Full safe demo — PowerShell runbook (`ping OK / browser fails` scenario) |
| **`docs/platform_api_contract.md`** | `/platform/*` schemas, RBAC headers, safety rules |

### Enterprise platform demo upgrade (portfolio interview story)

Additive layers on top of the same **`platform_data/*.jsonl`** backbone — beginner **`.bat`** flows untouched:

- **Incident clustering** (`platform_core/incidents.py`) feeds **`incident_cluster_count`** / **`affected_endpoint_count`** in **`GET /platform/metrics`** (deterministic grouping by category + signal fingerprint + time window).
- **RBAC lite** (`platform_core/rbac.py`) gated **`POST /platform/remediation/preview|execute`** + **`GET /platform/audit`** via **`X-Operator-Role`** / **`X-Operator-Id`** (default missing header ⇒ **`operator`**, **`admin`** for live repair + audits in demos).
- **Remediation registry** (`platform_core/remediation_registry.py`) is the authoritative allowlist (risk tier, **`api_execute_allowed`**, **`manual_only`**, confirmation phrases); legacy action aliases (`reset_firewall` → `firewall_reset_manual_only`) stay compatible with tests.
- **Metrics plus** aggregates dry-run executions, blocked audit rows, success / false-positive rates when JSONL signals exist — still **purely local** reads.
- **Dashboard polish** (`frontend/app/platform/page.tsx`) surfaces health, clustered KPI tiles, failure tables, optional preview sandbox, RBAC-role selector (browser `localStorage`), and an explicit safety banner (**no uploads / no silent destructive automation**).

### Install (platform + backend tests)

```powershell
pip install -r failure_system\requirements.txt
pip install -r requirements-platform.txt
```

### Backend (includes `/platform/*` on same app)

From repo root (so `platform_core/` resolves):

```powershell
$env:PYTHONPATH = (Get-Location).Path
uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

**Health:**

`GET http://127.0.0.1:8000/platform/health`

### Agent (never executes repairs)

Writes local JSONL and optionally POSTs **sanitized** payloads to **`127.0.0.1` only**:

```powershell
python -m endpoint_agent --once
python -m endpoint_agent.agent --once
python -m endpoint_agent --once --api http://127.0.0.1:8000
python -m endpoint_agent --loop --interval 30
```

- **`ENDPOINT_AGENT_API`** — default base URL if `--api` omitted.  
- **`ENDPOINT_AGENT_DRY_RUN=1`** — skip HTTP posts.  
- **`PLATFORM_DATA_DIR`** — override JSONL directory for **`platform_core.storage`**.

### Demo (offline / safe JSONL exercises)

Uses fixtures only — **does not mutate network**:

```powershell
python -m platform_core.demo
scripts\demo_platform_flow.bat
```

### Operator dashboard (Next.js)

**`frontend/app/platform/page.tsx`** — simple **metrics** panel when backend is running (expects `NEXT_PUBLIC_PLATFORM_API=http://127.0.0.1:8000`). If unset, copy env from **`frontend/.env.local.example`** if present or set manually for local demos.

---

## Safety model (summary)

- **Diagnose first**; repairs are **preview + human confirmation** (typed phrases where implemented).  
- **Failure Knowledge System** does **not** run repair binaries.  
- **Platform `/platform/remediation/execute`** enforces **`platform_core/policy`**, **allowlisted scripts only**, **`dry_run` default safe** High-risk (**firewall**, **arbitrary_command**) blocked from execution via API path.  
- **No automatic firewall reset** / **silent adapter disable** / **opaque shell from API**.  
- **Logs stay local** — do not commit real **`logs/`**, **`reports/`**, **`data/failure_blocks/*.jsonl`**, **`platform_data/*.jsonl`**.

Full write-ups: **`docs/safety_model.md`**, **`docs/safety_and_privacy.md`**.

---

## Demo scenario — platform flow (safe)

1. Start backend (`uvicorn` above).  
2. `python -m platform_core.demo` — loads fixtures → heartbeat/snapshot/events → remediation **preview** → shows **blocked** high-risk attempt → optional **dry_run** execution.  
3. Browse **`/platform/metrics`** and **`frontend` `/platform`** page.  
4. Run **`python -m endpoint_agent --once --api ...`** with **`ENDPOINT_AGENT_DRY_RUN=1`** first to verify payloads without writes.

---

## Development guide

### Run tests

```powershell
pip install -r failure_system\requirements.txt
pip install -r requirements-platform.txt
$env:PYTHONPATH = (Get-Location).Path
pytest -q
```

CI: **`.github/workflows/ci.yml`** (pytest only; **no** Windows repair scripts).

### Repository layout (high level)

```text
docs/                       # Architecture, safety, platforms
scripts/proxy_guard/        # Diagnose / reset / monitor / safe Cursor launcher (no Python)
failure_system/             # FailureBlock JSONL knowledge product
platform_core/              # Platform domain models, policy, privacy, JSONL storage
endpoint_agent/             # Local collector; optional localhost API POST
backend/                    # FastAPI SaaS demo + /platform router
frontend/                   # Next.js demo + app/platform dashboard
scripts/                    # Windows .bat (beginner toolkit)
src/                        # python -m src CLI
tests/                      # pytest
platform_data/              # Local JSONL for platform prototype (mostly gitignored)
```

### Documentation index

| Topic | Doc |
| --- | --- |
| Interview case study | [`docs/interview_case_study.md`](docs/interview_case_study.md) |
| Core architecture | [`docs/architecture.md`](docs/architecture.md) |
| FailureBlock contract | [`docs/failure_block_contract.md`](docs/failure_block_contract.md) |
| Safety | [`docs/safety_model.md`](docs/safety_model.md) |
| Interview pitch | [`docs/interview_pitch.md`](docs/interview_pitch.md) |
| Platform API contract | [`docs/platform_api_contract.md`](docs/platform_api_contract.md) |
| Safe demo walkthrough | [`docs/demo_walkthrough.md`](docs/demo_walkthrough.md) |
| Proxy Guard (Windows scripts + Python CLI) | [`docs/proxy_guard.md`](docs/proxy_guard.md) |
| Docs hub | [`docs/README.md`](docs/README.md) |

---

## Project overview — three faces

| Face | Purpose |
| --- | --- |
| **Scripts** | Fast human workflows on Windows. |
| **`python -m src` + FKS** | Explainable diagnostics and knowledge records. |
| **Platform prototype** | Policy-gated previews, audit JSONL, optional localhost dashboard. |

Resume one-liner (see **`docs/interview_case_study.md`**):

> Deterministic Windows network diagnostics and FailureBlocks with a **privacy-aware, policy-gated remediation preview** prototype—**human-confirmed** repairs only.

---

## Optional demos (not required for toolkit)

| Area | README |
| --- | --- |
| SaaS / SQLite backend | **`backend/`** |
| Frontend | **`frontend/`** |
| Legacy demo agent | **`agent/`** |
| Hybrid network agent | **`network_agent/`** |

---

## License

MIT — see [`LICENSE`](LICENSE).
