# Windows Network Recovery Toolkit

Beginner-friendly Windows 10/11 network diagnosis and repair scripts for common issues such as proxy failures, DNS cache problems, Winsock corruption, and cases where ping works but browsers or `curl` fail.

## Project Status

- Platform: Windows 10 and Windows 11
- Dependencies (interactive toolkit): built-in Windows commands for `.bat` flows
- Optional: Python **3.10+** — `src/` decision engine stays stdlib-only; **`failure_system`** adds Pydantic + FastAPI for FailureBlocks (see `failure_system/requirements.txt`)
- Primary interface: `.bat` scripts plus `scripts\decision_engine.bat` wrappers
- Default mode: diagnose first, repair only after confirmation
- Safety boundary: does not disable adapter bindings and does not reset firewall automatically

## Failure Knowledge System (`failure_system`)

Structured **FailureBlocks** turn raw Windows diagnostics into searchable, ranked knowledge (similar in spirit to Blockify-style idea blocks): signals → causes → confidence → **recommended_fix** with explicit **risk_level**, **safety_boundary**, and **rollback_plan**. Repairs never run from this layer unless a human confirms separate toolkit actions.

### Architecture (text diagram)

```text
┌─────────────────────┐     ┌──────────────────┐     ┌─────────────────────┐
│ Diagnostic collector│ ──► │ RuleEngine       │ ──► │ FailureBlock gen    │
│ (read-only probes)  │     │ (signals→causes) │     │ (typed artefact)    │
└─────────┬───────────┘     └──────────────────┘     └──────────┬──────────┘
          │                                                        │
          │                                                        ▼
          │                                             ┌─────────────────────┐
          └────────────────────────────────────────────►│ JSONL shards        │
                                                        │ data/failure_blocks │
                                                        │ YYYY-MM-DD.jsonl    │
                                                        └──────────┬──────────┘
                                                                   │
                          ┌────────────────────────────────────────┼────────────────────────┐
                          ▼                    ▼                     ▼                        │
                   Search index           FastAPI                    CLI                     │
                   (token AND match)     `/diagnose` ...           `python -m failure_system`│
```

### Quick start

```powershell
cd C:\Users\Zixsa\Kozphy\Windows-Network-Recovery-Toolkit
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r failure_system\requirements.txt

# Single-machine diagnostics + persist FailureBlock JSONL (no repairs)
python -m failure_system diagnose
python -m failure_system search "browser fails"
python -m failure_system recommend --query "dns"

# HTTP API (same safety: probes only; no repair execution)
uvicorn failure_system.api:app --host 127.0.0.1 --port 8010
```

| Endpoint | Purpose |
| --- | --- |
| `GET /health` | Liveness + package version |
| `POST /diagnose` | Run safe probes; persist FailureBlock JSONL |
| `GET /failure-blocks` | Recent block summaries (sorted newest first) |
| `GET /failure-blocks/search?q=` | Full-text token search over stored blocks |
| `POST /recommend-fix` | Body: `{ "failure_block_id": "<uuid>" }` or `{ "query": "..." }` — returns rationale + risk (no execution) |

Optional: `set FAILURE_SYSTEM_DATA_DIR=C:\path\to\failure_blocks_root` to override the default `<repo>\data\failure_blocks`.

### Example FailureBlock (trimmed)

```json
{
  "id": "00000000-0000-0000-0000-000000000000",
  "name": "DNS resolution failure",
  "symptom": "Ping OK but DNS lookup fails.",
  "observed_signals": ["ping_ip=ok", "nslookup=fail", "curl_https=fail"],
  "likely_causes": ["DNS resolution failure"],
  "confidence_score": 0.88,
  "recommended_fix": "Safe first step: run `scripts/reset_dns.bat` ... after reviewing context.",
  "risk_level": "low",
  "safety_boundary": "This Failure Knowledge System runs read-only diagnostics only...",
  "rollback_plan": "Note prior DNS server list; restore static DNS if changed...",
  "created_at": "2026-05-02T12:00:00+00:00",
  "source_logs": ["rules:dns_failure_likely", "explain:..."]
}
```

### Example diagnosis flow

1. Operator runs `python -m failure_system diagnose` (or `POST /diagnose`).
2. Collector runs **safe** commands only: `ping`, `nslookup`, `curl`, `ipconfig /all`, `netsh winhttp show proxy`, `route print`.
3. **RuleEngine** maps booleans (ping/DNS/HTTPS/proxy) plus optional **intermittent** flag to ranked causes with confidence and narrative explanation.
4. **FailureBlock** is generated, appended to `data/failure_blocks/<UTC-date>.jsonl`.
5. Search (`GET /failure-blocks/search?q=` or CLI `search`) retrieves historical blocks; `recommend` surfaces textual fix guidance **without** invoking `.bat` repairs.

### Safety boundary (Failure Knowledge System)

- **No automatic repair**: scripts such as `reset_dns.bat`, `reset_proxy.bat`, Winsock/TCP/IP resets, or firewall changes are never executed by this package.
- **Risk labels**: each block carries `risk_level` (`low` / `medium` / `high`) for the *recommended human action*, not network uptime.
- **Rollback**: every block includes rollback notes where state-changing fixes would apply; diagnostics-only runs state that no mutation occurred.
- **Data hygiene**: JSONL is gitignored; avoid pasting real corporate hostnames or secrets into shared logs.

### Interview explanation (one paragraph)

This adds a **knowledge plane** on top of imperative `.bat` tooling: diagnostics become normalized **FailureBlocks** with provenance-friendly fields (signals, confidence, fix text, risk, rollback). A deterministic **rule engine** replaces opaque scoring with explainable mappings—DNS vs HTTPS-path vs proxy symptoms—stored as append-only **JSONL** for local retrieval and ranking. A thin **FastAPI** and **CLI** expose the same contracts so ops can automate collection while keeping repairs behind explicit human confirmation, matching enterprise safety expectations for platform tooling.

## Network Observability & Recovery Agent

This toolkit now exposes a structured **observe → attribute → decide → preview → remediate** path on Windows for DNS, proxy, browser-path, TCP/TLS, Winsock-adjacent, and socket-churn clues. Signals stay local (`reports/`, `logs/`), use deterministic hypotheses (no ML), and reinforce the same conservative safety defaults as `.bat` flows (diagnose-first, typed confirmations for HKCU edits, never automatic firewall resets, never silent adapter disables).

Representative workflows:

```powershell
python -m src snapshot
python -m src diagnose-live
python -m src proxy-status
python -m src proxy-owner
python -m src proxy-monitor --interval 5 --jsonl logs/proxy_guard_events.jsonl
python -m src proxy-disable --dry-run
```

Companion docs live in `docs/proxy_guard.md`, `docs/localhost_proxy_timeout_case.md`, `docs/process_attribution.md`, and `docs/decision_engine_v2.md`.

## Decision Architecture v1 (auditable CLI)

Structured decision layer adds **features → scores → explanations → tiered repairs → audit/feedback**.
It is deliberately small: readable rules with explicit evidence strings, probability-like scores in `[0.0, 1.0]`, and append-only JSONL logs that never leave your machine unless you choose to upload them manually.

Concise implementation plan (what landed in-repo):

| Layer | Role |
| --- | --- |
| `src/diagnostics/` | Windows probes (`ping`, `nslookup`, `curl`, WinHTTP/registry/PowerShell) → normalized `FeatureVector` |
| `src/decision_engine/` | Deterministic bumps + clamps per hypothesis (DNS/proxy/Winsock/firewall/adapter/ISP‑router/browser-only) |
| `src/recommendations/` | Safe vs guided vs advanced script pointers (advanced items are informational only here) |
| `src/logging/` | `logs/decision_audit.jsonl` + `logs/decision_feedback.jsonl` |
| `reports/` | `last_diagnosis.json` snapshot for subsequent subcommands |

### Features (representative signals)

Examples: `ping_ip_ok`, `ping_domain_ok`, `nslookup_ok`, `tcp_443_ok`, `browser_http_ok` (HTTPS `curl`), `proxy_enabled`,
`winhttp_proxy_enabled`, `dns_servers_detected`, `adapter_connected`, `gateway_reachable`, workload counters (`time_wait_*`).

Machine identity in audit logs is a **truncated SHA-256 fingerprint** derived from hostname + kernel version + CPU arch (never raw hostnames).

### CLI entry points (`python -m src <subcommand>`)

| Command | Purpose |
| --- | --- |
| `diagnose` | Probe or load `--fixture`, score, persist `reports/last_diagnosis.json`, append audit JSONL |
| `explain` | Print rationale for `last_diagnosis.json` (add `--live` for `last_diagnosis_live.json`) |
| `recommend` | Print tier buckets (`--live` reads v2 artefact recommendations) |
| `repair-safe` | Preview safe-tier items; `--apply` can launch the **first LOW-risk `.bat`** after typing `RUN` |
| `repair-preview` | Preview tiers from **`last_diagnosis_live.json` first**, else fallback to v1 artefact |
| `repair-apply` | Interactive `RUN` flow for first LOW-tier script (`--dry-run` lists candidates only) |
| `snapshot` | Persist `reports/snapshots/<UTC>.json` + append `logs/network_snapshots.jsonl` |
| `diagnose-live` | Build snapshot → v2 hypotheses → `reports/last_diagnosis_live.json` + richer JSONL |
| `proxy-status` | HKCU WinINET proxy normalization (`--json` machine-readable for APIs) |
| `proxy-owner` | Listener attribution for localhost proxy ports (`netstat`, `tasklist`, optional CIM) |
| `proxy-monitor` | Poll registry deltas (optional `--jsonl` sink) |
| `proxy-disable` | Typed `DISABLE_PROXY` confirmation; WinINET HKCU-only (`--clear-server` optional) |
| `feedback` | Persist outcome rows for calibration (`diagnosis_id`, action, outcome) |
| `export-report` | Human-readable plaintext under `reports/` |

Beginner wrappers live in `scripts\decision_engine.bat` forwarding to Python.

Safety notes for this CLI (mirrors toolkit policy):

- No automatic firewall reset, no disabling adapters silently, no external log upload wiring.
- `repair-safe --apply` only considers scripts under `scripts/` with **LOW** risk flagged by the recommendation engine.
- Guided/advanced actions stay in batch tooling (`auto_fix.bat`, targeted scripts) where humans confirm changes.

Example (offline scoring using a bundled fixture):

```powershell
cd C:\Users\Zixsa\Kozphy\Windows-Network-Recovery-Toolkit

python -m src diagnose --fixture tests\fixtures\features_dns_issue.json
python -m src explain
python -m src recommend
python -m src export-report
```

Example (live Windows probes):

```powershell
cd C:\Users\Zixsa\Kozphy\Windows-Network-Recovery-Toolkit

python -m src diagnose
python -m src repair-safe              # preview only
python -m src repair-safe --apply      # prompts before launching first LOW-risk .bat

python -m src feedback --diagnosis-id "<uuid-from-last-run>" `
  --recommended-action "scripts/reset_dns.bat" `
  --user-feedback-fixed true `
  --notes "flush fixed browser"
```

Sample console output (fixture run, trimmed):

```text
=== Windows Network Recovery Toolkit - Decision Architecture ===
Diagnosis ID: <uuid>

Dns Issue confidence 0.84 because IP reachability succeeds while nslookup google.com fails.
(ping_ip=ok, nslookup=fail, curl_https=fail, proxy=off, adapter_up=yes).

Root cause ranking (confidence):
  - dns_issue: 0.84
  - browser_only_issue: 0.06
  ...
```

Unit tests for scoring live in `tests/test_decision_scoring.py` with JSON fixtures under `tests/fixtures/features_*.json`.

## Quick Start

1. Download the repository as a ZIP file or clone it with Git.
2. Open the `scripts` folder.
3. Right-click `auto_diagnose.bat`.
4. Select **Run as administrator**.
5. Read the diagnosis and recommendation.
6. To apply a guided repair, right-click `auto_fix.bat` and select **Run as administrator**.
7. Restart Windows if the script tells you to.

## Run Full Stack Locally (Backend + Frontend + Agent)

This section is optional. If you only need the Windows repair toolkit, use the `Quick Start` and `.bat` scripts above.

If you want to run the SaaS demo stack in this repository, start three terminals in this order.

From PowerShell:

```powershell
cd C:\Users\Zixsa\Kozphy\Windows-Network-Recovery-Toolkit
```

Terminal A - Backend (FastAPI):

```powershell
cd C:\Users\Zixsa\Kozphy\Windows-Network-Recovery-Toolkit
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt

# Local development auth bypass (optional but useful for local testing)
$env:AUTH_BYPASS_USER_ID="dev-user-1"
$env:AUTH_BYPASS_EMAIL="dev@example.com"

uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Backend URLs:

- `http://localhost:8000`
- `http://localhost:8000/docs`

Terminal B - Frontend (Next.js):

```powershell
cd C:\Users\Zixsa\Kozphy\Windows-Network-Recovery-Toolkit\frontend
Copy-Item .env.local.example .env.local -Force
npm install
npm run dev
```

Frontend URL:

- `http://localhost:3000`

Terminal C - Agent (Python):

```powershell
cd C:\Users\Zixsa\Kozphy\Windows-Network-Recovery-Toolkit
.\.venv\Scripts\Activate.ps1
pip install -r agent\requirements.txt
python agent\agent.py --api http://localhost:8000 --loop --interval 10
```

Quick health check:

- Open `http://localhost:8000/docs` to confirm backend is running.
- Open `http://localhost:3000` to confirm frontend is running.
- Confirm the agent terminal prints diagnose and monitor responses.

## Recommended Workflow

Use the smallest safe action that matches the diagnosis.

1. Diagnose: run `auto_diagnose.bat`.
2. Repair with guidance: run `auto_fix.bat`.
3. Repair manually: run a targeted script such as `reset_dns.bat` or `reset_proxy.bat`.
4. Fallback repair: run `one_click_fix.bat` when the issue points to Winsock, TCP/IP, or an unclear stack problem.
5. Manual last resort: run `reset_firewall.bat` only when firewall rules are likely broken.

## Automatic Diagnosis Mode

`auto_diagnose.bat` is read-only. It collects evidence, classifies the likely problem, and writes a timestamped log to `logs/`.

It checks:

- Current network adapters
- DNS with `nslookup google.com`
- TCP 443 with PowerShell `Test-NetConnection`
- HTTPS with `curl https://www.google.com`
- WinHTTP proxy configuration
- User proxy registry values

`auto_fix.bat` runs the diagnosis first, shows the recommendation, asks for confirmation, and then calls the matching repair script. It never runs `reset_firewall.bat` automatically.

## Root Cause Monitoring Mode

Some network failures are not immediate. The system can work at startup, then fail later after proxy policy changes, process startup, or connectivity transitions.

Use `monitor_network.ps1` to capture these state changes over time.

What it monitors:

- WinHTTP proxy state
- User proxy registry values (`ProxyEnable`, `ProxyServer`, `AutoConfigURL`, `AutoDetect`)
- TCP 443 reachability (`Test-NetConnection`)
- HTTPS status (`curl`)
- Recent process starts (last 5)

How to run:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\monitor_network.ps1
```

Optional interval (script clamps to 5-10 seconds):

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\monitor_network.ps1 -IntervalSeconds 8
```

Log file:

- `logs/network_monitor.log`

How to interpret logs:

- Each cycle appends a full snapshot with timestamped sections.
- `!!! CHANGE DETECTED !!!` means monitored state changed since previous cycle.
- Focus on transitions:
  - `ProxyEnable` changes
  - `ProxyServer` appears
  - `AutoDetect` flips from `0` to `1`
  - TCP 443 changes from `True` to `False`
  - `curl` changes from success to timeout/failure
- Correlate these changes with the "Recent Processes" block to identify likely triggers.

## When To Use This

Use this toolkit when Windows says the network is connected, but internet access is still broken or inconsistent.

Common examples:

- Browser shows `ERR_PROXY_CONNECTION_FAILED`
- `ping 8.8.8.8` works, but websites do not load
- `curl` fails even though Wi-Fi or Ethernet is connected
- DNS lookups fail or behave inconsistently
- Problems start after VPN, proxy, antivirus, or cleanup tools
- Some apps connect while browsers fail

## Script Reference

| Script | Mode | Use Case |
| --- | --- | --- |
| `auto_diagnose.bat` | Read-only | Collect evidence and recommend the likely fix. |
| `auto_fix.bat` | Guided repair | Diagnose first, then ask before running the recommended repair. |
| `classify_root_cause.bat` | Decision | Automatically infers root cause from diagnostic data. |
| `recommend_fix.bat` | Decision | Suggests safest fix based on diagnosis. |
| `decision_engine.bat` | Decision | Python decision architecture (`diagnose`, `explain`, `recommend`, `repair-safe`, `feedback`, `export-report`). |
| `snapshot_network.bat` | Observability | Writes `reports/snapshots/` JSON via Python `snapshot`. |
| `diagnose_live.bat` | Observability | Runs `python -m src diagnose-live` (+ v2 artefacts). |
| `proxy_status.bat` | Observability | Human-readable HKCU proxy status. |
| `proxy_owner.bat` | Attribution | Listener owners for localhost proxy ports. |
| `proxy_monitor.bat` | Observability | Wrapper for CLI `proxy-monitor` (supports interval + optional JSONL path). |
| `proxy_disable.bat` | Guided repair | Launcher for typed-phrase HKCU proxy disable (passes `%*` to CLI). |
| `check_network.bat` | Read-only | Run a simpler manual connectivity check. |
| `monitor_connections.bat` | Observability | Real-time TCP connection monitoring. |
| `anomaly_monitor.bat` | Observability | Detects abnormal connection behavior. |
| `monitor_network.ps1` | Root Cause Monitoring | Tracks proxy and connectivity state changes over time. |
| `check_connection_exhaustion.bat` | Read-only | Detects socket leaks and connection exhaustion issues. |
| `detect_code_leak.bat` | Dev Tool | Detects possible connection leak patterns in code. |
| `reset_dns.bat` | Targeted repair | Flush DNS cache and show DNS configuration. |
| `reset_proxy.bat` | Targeted repair | Clear WinHTTP and user-level proxy settings. |
| `one_click_fix.bat` | Full repair | Reset Winsock, TCP/IP, DNS cache, and proxy settings. |
| `reset_firewall.bat` | Manual repair | Reset Windows Firewall rules to defaults after confirmation. |

## Expected Outcomes

After the correct repair and restart when required:

- Browsers load websites again.
- `curl` can reach HTTPS websites.
- DNS lookups succeed.
- WinHTTP proxy shows direct access when no proxy is required.
- Proxy-related browser errors stop appearing.

## Safety Model

This project follows conservative repair defaults.

- Administrator access is required for repair scripts.
- Diagnosis is read-only.
- Guided repair asks before making changes.
- Firewall reset is never automatic.
- Full stack repair reminds the user to restart.
- Logs are written locally and ignored by Git.

For more detail, read `docs/safety_model.md`.

## Documentation

- `docs/script_reference.md`: detailed script behavior and expected output.
- `docs/diagnosis_decision_tree.md`: how automatic diagnosis maps symptoms to recommendations.
- `docs/operational_runbook.md`: step-by-step runbook for real troubleshooting.
- `docs/design_principles.md`: design goals, safety boundaries, and tradeoffs.
- `docs/system_architecture.md`: high-level architecture, layered model, and decision flow.
- `docs/faq.md`: beginner-friendly answers to common questions.
- `docs/troubleshooting_flow.md`: manual troubleshooting flow.
- `docs/proxy_error.md`: `ERR_PROXY_CONNECTION_FAILED` explanation and fixes.
- `docs/ping_ok_but_browser_fails.md`: why ping can work while browsers fail.
- `docs/proxy_guard.md`: Proxy Guard HKCU watcher + JSONL/events.
- `docs/localhost_proxy_timeout_case.md`: Chromium timeout + localhost proxy walkthrough.
- `docs/process_attribution.md`: netstat/tasklist/CIM attribution limits.
- `docs/decision_engine_v2.md`: live hypothesis scoring contract.

## Repository Layout

```text
Windows-Network-Recovery-Toolkit/
├── README.md
├── LICENSE
├── CHANGELOG.md
├── CONTRIBUTING.md
├── SECURITY.md
├── docs/
├── agent/                 # optional SaaS demo agent (unchanged)
├── backend/               # optional SaaS/API demo (delegates toolkit routes to `python -m src`)
├── failure_system/        # Failure Knowledge System (FailureBlocks, FastAPI, CLI)
├── data/failure_blocks/   # local JSONL shards (gitignored `*.jsonl`)
├── src/                   # stdlib toolkit + observability (see below)
│   ├── core/
│   ├── diagnostics/
│   ├── observability/
│   ├── attribution/
│   ├── proxy_guard/
│   ├── repair/
│   ├── decision_engine/
│   ├── recommendations/
│   ├── logging/
│   └── command_handlers.py  # wired from cli.py for v2 ergonomics
├── tests/                 # pytest + feature fixtures
├── reports/               # generated diagnosis snapshots (gitignored)
├── logs/
└── scripts/
```

## Hybrid Agent Architecture (Current)

The repository currently contains two related tracks:

- Legacy beginner-first `.bat` workflows for direct Windows troubleshooting.
- Python hybrid-agent workflows (`network_agent/`) with API and report-driven UI.

Operational flow for the hybrid path:

1. Collect signals from Windows commands (`network_agent/collectors/`).
2. Rank likely issues with deterministic confidence rules (`network_agent/engine/`).
3. Persist JSON reports (`network_agent/reports/`).
4. Expose diagnosis/preview/execute/report routes (`network_agent/api.py`).
5. Render operator workflow in browser (`hybrid_frontend/`).

### Safety Boundaries (Hybrid Path)

- Diagnose is read-only and runs before any repair guidance.
- Repair preview is required by UI workflow and available via API.
- Repair execute requires explicit `confirm: true` in backend request payload.
- No automatic firewall reset path is exposed in hybrid policy.
- Backend policy remains source of truth; frontend does not bypass it.

### Audit Notes (Hybrid Path)

- Decision evidence is returned with each diagnosis result and report.
- Report files are timestamped and saved as JSON under `reports/`.
- Failures in command execution are surfaced through API error payloads and
  command-level return codes in repair execution responses.
- Recovery path for incorrect diagnosis: rerun diagnose, inspect report evidence,
  preview safer alternatives, then execute only after confirmation.

## Portfolio Value

This project demonstrates practical engineering skills:

- Debugging: separates DNS, proxy, TCP, HTTPS, browser, and firewall symptoms.
- Automation: turns repeated Windows repair commands into guided workflows.
- Product thinking: supports non-expert users with clear messages and safe defaults.
- Documentation: includes runbooks, decision trees, safety notes, and contribution guidance.

## Compatibility

- Windows 10
- Windows 11
- Command Prompt or PowerShell
- Administrator permissions for repair scripts

## License

This project is licensed under the MIT License. See `LICENSE` for details.
