# Replay model

## Principle

Replay recomputes **deterministic** decisions from **stored observations** without opening sockets, `reg.exe`, or curl probes.

## CLI surfaces

| Command | Source file | Schema |
| --- | --- | --- |
| `python -m src replay <run_id>` | `logs/decision_runs.jsonl` | `live_run_audit_v1` |
| `platform_core.reasoning_audit.replay_reasoning_record` | `platform_data/reasoning_runs.jsonl` | `reasoning_run` |
| `platform_core.event_store.replay_timeline` | `logs/events.jsonl` + `logs/decisions.jsonl` | `platform_event_store.v1` |
| `GET /platform/replay/{run_id}` | platform DB / JSONL | diagnosis store |

## Match criteria

Replay **passes** when recomputed hypothesis order, confidence bands, and policy fields match stored rows within documented tolerances.

Replay **fails** when:

- scorer weights changed in code
- audit row missing or corrupt JSONL line
- observations blob incomplete

## What replay does not do

- Re-run Proof Engine curl contrasts (unless explicitly encoded as stored proof outcomes)
- Mutate registry or network state
- Prove historical registry writer identity retroactively

## Unified timeline

```powershell
python -c "from pathlib import Path; from platform_core.event_store import replay_timeline; import json; print(json.dumps(replay_timeline(Path('.'), 'YOUR_RUN_ID'), indent=2))"
```
