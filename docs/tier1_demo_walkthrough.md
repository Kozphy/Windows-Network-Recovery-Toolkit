# Tier-1 demo walkthrough (~10 minutes)

Production-shaped flow for portfolio reviewers. All steps are **read-only or preview-only** unless you explicitly confirm execute.

## Prerequisites

```powershell
pip install -e ".[dev]"
$env:PYTHONPATH = (Get-Location).Path
python -m platform_core.demo_fleet --seed
```

## 1. Read-only diagnosis

```powershell
python -m src diagnose --fixture tests/fixtures/features_healthy_signals.json
python -m src proxy registry-writer-proof --json
```

## 2. Evidence tree / reasoning (offline)

```powershell
python -c "from platform_core.reasoning_engine import observation, run_reasoning; from platform_core.diagnosis_text import render_reasoning_summary; o=[observation('browser_https_failed'),observation('wininet_proxy_enabled'),observation('proxy_bypass_succeeded')]; print(render_reasoning_summary(run_reasoning(o)))"
```

## 3. Telemetry proof contrast

```powershell
python -m telemetry.cli fuse-registry-writer-evidence `
  --events tests/fixtures/telemetry/sysmon_event13_proxy_server_node.json `
  --listener tests/fixtures/telemetry/listener_node.json `
  --proxy-change-time 2026-01-15T12:00:10Z `
  --pretty
```

Compare with listener-only (no writer proof):

```powershell
python -m telemetry.cli fuse-registry-writer-evidence `
  --listener tests/fixtures/telemetry/listener_node.json `
  --proxy-change-time 2026-01-15T12:00:10Z `
  --events tests/fixtures/telemetry/missing_fields.json `
  --pretty
```

## 4. Policy decision + remediation preview

```powershell
pytest -q tests/test_policy_safety_contract.py tests/test_api_dry_run_default.py
python -m src repair preview --fixture tests/fixtures/platform/proxy_loopback_enabled.json
```

## 5. Audit JSONL

Inspect append-only rows (local, gitignored):

- `platform_data/audit.jsonl`
- `logs/registry_writer_evidence.jsonl`

## 6. Replay

```powershell
python -m platform_core.replay.runner --help
pytest -q tests/replay/test_replay_determinism.py
```

## 7. Dashboard / platform API

```powershell
uvicorn backend.main:app --port 8000
# GET /platform/endpoints
# GET /platform/metrics  (includes reliability_metrics)
# GET /platform/incidents
```

Optional frontend: `frontend/` Next.js platform page.

## Safety reminder

Nothing in this demo silently kills processes, resets firewall, disables adapters, or mutates registry without typed confirmation.
