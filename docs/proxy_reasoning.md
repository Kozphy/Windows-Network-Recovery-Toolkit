# Proxy Attribute & Evidence Reasoning

Production-oriented module: **`proxy_reasoning/`**

## Principle

**Observation ≠ Inference ≠ Proof**

- Listener/process metadata is **heuristic attribution**, not registry-writer proof.
- Localhost proxies (including `node.exe`) are **not** labeled malicious without proof-tier certificate/persistence evidence.
- Policy decisions are **separate** from diagnosis.

## Pipeline

```
Signal → Event → Hypothesis → Evidence → Verification → Confidence Boundary → Policy → Audit JSONL
```

Entry point:

```python
from proxy_reasoning import run_proxy_reasoning, append_proxy_reasoning_run

run = run_proxy_reasoning(payload={...}, requested_action="diagnose")
append_proxy_reasoning_run(run)
```

Replay (no re-probe):

```python
from proxy_reasoning.audit import replay_proxy_reasoning_record, iter_proxy_reasoning_records

for record in iter_proxy_reasoning_records():
    replayed = replay_proxy_reasoning_record(record)
```

## Canonical scenarios

| Case ID | Pattern |
|---------|---------|
| `CASE_WININET_PROXY_DRIFT` | WinINET on, localhost/unexpected server, WinHTTP may be direct |
| `CASE_LOCALHOST_PROXY_LISTENER` | Loopback proxy + optional listener attribution |
| `CASE_BROWSER_PROXY_PATH_ISSUE` | Ping/DNS ok, browser path fails, bypass may succeed |
| `CASE_ELECTRON_APP_PROXY_FIREWALL_INTERACTION` | Browser ok, Electron app fails; firewall relief is observational only |

## Audit sink

Default: `logs/proxy_reasoning_audit.jsonl`

Example record: `examples/proxy_reasoning_audit_record.json`

## Integration

- Reuses collector-shaped dicts compatible with `proxy_guard` scan output and `python -m src` snapshots.
- Does **not** replace `platform_core.reasoning_engine` fleet scenarios; use this module for **proxy-first** attribute modeling.
- Existing `infer_proxy_risk` remains available; `build_proxy_entity()` maps scan payloads into the canonical entity.

## Policy summary

| Outcome | Examples |
|---------|----------|
| **ALLOW** | `diagnose`, `snapshot`, `remediation_preview`, confirmed low-risk `restore_proxy` |
| **PREVIEW** | `clear_winhttp_proxy`, firewall rule cleanup preview, unverified mutations |
| **BLOCK** | `kill`, `delete_cert`, `reset_firewall`, arbitrary shell, unlisted actions |
