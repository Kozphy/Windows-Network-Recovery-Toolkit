# Golden path demo

A local-first Endpoint Reliability Platform for deterministic Windows network diagnostics, structured FailureBlocks, policy-gated remediation preview, privacy-aware audit events, and replayable incident analysis.

## Flow

1. **Collect** — `endpoint_agent` or CLI writes scrubbed snapshots / failure events.
2. **Normalize** — optional producers append `NormalizedEvent` rows to `platform_data/normalized_events.jsonl` via `append_event`.
3. **Diagnose** — operators review `/platform/events` + dashboard tables.
4. **Preview** — `POST /platform/remediation/preview` (FailureBlock-driven).
5. **Gate** — `evaluate` surfaces `reason_codes` + confirmation requirements.
6. **Execute (optional)** — admin + phrase + allowlisted batch only.
7. **Replay** — `python -m platform_core.replay --input …` or inline API preview for regression analysis.

## Quick commands

```powershell
# Backend
uvicorn backend.main:app --reload --port 8000

# Replay sample file
python -m platform_core.replay --input tests/fixtures/platform/proxy_loopback_enabled.json

# Pytest gate & bus
pytest tests/test_platform_faang_upgrade.py -q
```

Privacy banner: raw hostnames usernames and private IPs must not enter JSONL without passing `privacy.py` helpers.
