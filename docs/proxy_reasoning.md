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

## Failure modes

| Symptom | Likely cause | Safe recovery |
| --- | --- | --- |
| Policy `BLOCK` for `restore_proxy` | Verification not `CONFIRMED` | Re-run probes; use `diagnose-live` proofs before retry |
| Replay differs from live run | Signals frozen in audit row | Expected — replay does not re-probe; compare `signals` block |
| Empty hypothesis list | Payload missing proxy/listener fields | Validate collector dict matches `build_proxy_entity` expectations |
| Iterator skips lines | Corrupt JSONL tail | Repair or truncate bad line; re-append from known good offset |

## Audit notes for reviewers

- Default sink: `logs/proxy_reasoning_audit.jsonl` (append-only).
- `proof_hints` duplicates entity evidence attributes — verify against raw `signals`, not summary text alone.
- `CONFIRMED` on a verification check means the check passed, **not** benign/malicious intent.
- Policy outcome is independent of `user_visible_summary` — log both when demonstrating compliance.
- Destructive tokens (`kill`, `delete_cert`, `reset_firewall`) must remain `BLOCK` without explicit product approval.

## Related workflow

For markdown incident reports (read-only, no policy engine), see [`proxy_investigation_workflow.md`](proxy_investigation_workflow.md).
