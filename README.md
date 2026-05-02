# Windows Network Recovery Toolkit

**Local-first Windows network diagnostics** with a beginner **`.bat` toolkit**, an advanced **`python -m src` decision CLI**, the **Failure Knowledge System** (**FailureBlocks** + JSONL), and an optional **Endpoint Reliability Platform** layer (`platform_core/`, **`python -m endpoint_agent`**, **`/platform/*` API**) for portfolio-style observability—**still no silent destructive repair** and **no default log uploads**.

### Orienting in ~10 minutes (read-only)

1. Skim **`docs/README.md`** for the docs map (architecture, FailureBlock contract, proxy guard, platform API).
2. Pick your surface:
   - **Beginner tooling:** `scripts/*.bat`, especially `scripts/proxy_guard/*`.
   - **Explainable diagnostics:** **`python -m src`** paths and **`failure_system`** (`docs/architecture.md`, `docs/safety_model.md`).
   - **Optional platform prototype:** `platform_core/`, **`backend`** + **`frontend`**, **`docs/endpoint_reliability_platform.md`**.
3. For **deterministic regression & safety assertions** exercised in CI, see **`docs/test_strategy.md`** (no destructive scripts, no privileged operations in those flows).

Then continue with Quick start below for the path that matches your role.

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

**Recommended workflow:** **Diagnose → Save Known Good → Monitor → Diff → Restore** (batch scripts and/or Python CLI below). Optionally **Safe Cursor launcher** after you trust the posture.

Persist a baseline with the Python CLI (Windows):

- **`python -m src network-state snapshot save --name <label>`** → `logs/network_state_snapshots.jsonl`; **`network-state snapshot set-default --name …`** writes **`config/network_state_default.json`**. Drift/report/restore previews: **`docs/network_state_manager.md`** (`diff`, `report`, **`restore --confirm RESTORE_NETWORK_STATE`**).
- Legacy path: **`python -m src proxy-snapshot save --name <label> [--as-default]`** → `logs/proxy_known_good_snapshots.jsonl` (+ optional `config/last_known_good_proxy.json`). **`docs/proxy_known_good_snapshot.md`**.

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

Proxy observability (`proxy-status`, `proxy-owner`, `proxy-guard`) and **HKCU WinINET Endpoint Reliability**:

```powershell
python -m src proxy-status                      # HKCU snapshot + parsed modes
python -m src proxy-diagnose                    # FailureBlocks + optional listener probe
python -m src proxy-diagnose --json             # Machine payload (risk + attribution + blocks)
python -m src proxy-attribution                 # localhost proxy port → PID/name/path/cmdline (best-effort)
python -m src proxy-disable                     # Typed DISABLE_PROXY → snapshot + mutate + verification
python -m src proxy-rollback --snapshot-id ...  # Restore prior capture (typed RESTORE_WININET)
python -m src proxy-monitor
python -m src proxy-guard --interval 5
python -m src proxy-guard --interval 5 --auto-rollback --trust-current # optional LKG + live restore (prior-poll rollback)
python -m src proxy-snapshot save --name my-baseline --as-default        # HKCU/Git/npm/env + WinHTTP baseline
python -m src proxy-snapshot list / show / diff / restore               # restore: dry-run by default; live needs --confirm RESTORE_KNOWN_GOOD_PROXY (--dry-run forces preview)
python -m src proxy-guard --interval 5 --known-good my-baseline --dry-run-rollback
python -m src proxy-guard --interval 5 --known-good my-baseline --auto-rollback   # rollback to named snapshot instead of prior poll only
python -m src network-state snapshot save --name home-clean
python -m src network-state snapshot set-default --name home-clean
python -m src network-state diff --default --json
python -m src network-state report --since 24h
python -m src network-state restore --name home-clean --dry-run
python -m src network-state evidence import --file evidence.csv   # optional Procmon-style CSV
```

**Safety notes:** Listener attribution uses **Windows-native netstat/tasklist/PowerShell CIM** — not proof who wrote registry values. **`proxy-disable`** persists **`logs/proxy_snapshots.jsonl`** immediately before **`reg`** writes; rollback restores captured values/absences via argv-only **`reg`** (no firewall/adapter resets). Structured **`ProxyFailureBlock`** rows describe proxy risk (distinct from **`failure_system/`** FailureBlocks). See **`docs/proxy_guard.md`**.

`proxy-guard` follows **detect → best-effort attribute → decide (default deny) → optional rollback preview/apply → audit** (`logs/proxy_guard_pipeline_audit.jsonl` schema_version `1` plus legacy v2 sinks). On each registry change it attaches a **heuristic** `candidate_actor` (when optional **`pip install psutil`** is available)—**not proof** of the writer process; see **`docs/proxy_guard.md` § Process attribution**. Rollback restores the **prior poll** snapshot by default, or a **named `proxy-snapshot`** baseline when **`--known-good`** is set (never arbitrary shell commands). Typical flags:

- `python -m src proxy-guard --interval 5` — detect + stdout / control JSONL  
- `--dry-run` / `--dry-run-rollback` — no live `reg` / `netsh` restores  
- `--auto-rollback` — legacy toggle; live restore without extra phrase  
- `--rollback` — rollback path (`--rollback-confirm RESTORE_PROXY` needed for live `reg` restores unless `--auto-rollback` is also set)  

Consolidated rows also mirror to `reports/proxy_guard_watch.jsonl`, `reports/proxy_guard_actions.jsonl`,
and `logs/proxy_guard_audit.jsonl`; policy defaults prefer **`config/proxy_guard_policy.json`**. See **`docs/proxy_guard.md`**, **`docs/proxy_guard_attribution.md`** / **`docs/proxy_guard_rollback.md`**.

Docs: **`docs/architecture.md`**, **`docs/proxy_guard.md`**, **`docs/network_state_manager.md`**, **`docs/decision_engine_v2.md`**.

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
docs/                       # Architecture, safety, platforms, test strategy
scripts/proxy_guard/        # Diagnose / reset / monitor / safe Cursor launcher (no Python deps)
failure_system/             # Failure Knowledge System — FailureBlocks + JSONL + CLI/API
proxy_attribution/          # Standalone read-only proxy classifier CLI (portfolio helper)
network_agent/              # Optional hybrid collectors + repair policy scaffolding
hybrid_frontend/            # Lightweight static companion for hybrid demos (see hybrid_frontend/README.md)
platform_core/              # Endpoint Reliability prototype — models, policy, privacy, JSONL storage
endpoint_agent/             # Local collector; optional localhost API POST
backend/                    # FastAPI host — SaaS demo surfaces + SQLite + /platform router
frontend/                   # Next.js demo dashboard (platform page + shared API helpers)
scripts/                    # Windows .bat (beginner toolkit) outside proxy_guard/
src/                        # python -m src decision + Proxy Guard CLI
tests/                      # pytest (offline-safe; see docs/test_strategy.md)
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
| Test strategy & safety regression matrix | [`docs/test_strategy.md`](docs/test_strategy.md) |
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
