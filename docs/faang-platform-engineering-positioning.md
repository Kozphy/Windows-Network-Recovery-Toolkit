# FAANG platform engineering positioning

How to present this repository for **platform engineering**, **infra SRE**, and **developer productivity** interviews.

---

## Platform thesis

Windows network failures are a **platform reliability problem**: developers lose hours to "mystery connectivity" that is often proxy misconfiguration. This repo is **decision infrastructure** — not a one-off script — with:

- Canonical engines in `src/platform_core/`
- Thin JSON facades in `windows_network_toolkit/`
- Fixture-safe CI on Linux + live probes on Windows

---

## Architecture pattern

```text
CLI (JSON only) → facade → canonical engine → audit JSONL
```

| Layer | Location | Rule |
|-------|----------|------|
| CLI handlers | `windows_network_toolkit/cli.py` | Parse args, serialize JSON, exit codes |
| Facades | `windows_network_toolkit/*.py` | Delegate; no duplicated business logic |
| Engines | `src/platform_core/` | Classification, proof, policy, timeline |
| Legacy shim | `src/cli.py` | Deprecation stderr; delegates where ported |

Primary entry:

```powershell
python -m windows_network_toolkit proxy-status
```

---

## API contract discipline

- All WNT commands emit **valid JSON** on stdout
- Non-Windows returns structured `unsupported_platform` where applicable
- State-changing commands default **`dry_run=true`**
- Confirmation tokens are **typed strings**, not booleans

Tests: `tests/windows_network_toolkit/test_cli_json_contract.py`

---

## Reliability patterns

| Pattern | Implementation |
|---------|----------------|
| Idempotent reads | `proxy-status`, `proxy-owner` |
| Soft-fail audit | Writes to `.audit/` never crash commands |
| Deterministic fixtures | `tests/fixtures/enert/dead_proxy_59081.json` |
| Classification matrix | Parametrized pytest for all 12 primaries |
| Deprecation path | `src` → `windows_network_toolkit` with stderr notice |

---

## CI smoke (portfolio proof)

```yaml
pytest tests/platform_core/classification tests/windows_network_toolkit
python -m windows_network_toolkit proxy-status --fixture tests/fixtures/enert/dead_proxy_59081.json
python -m windows_network_toolkit proxy-disable --dry-run
python -m windows_network_toolkit diagnose --proof --fixture tests/fixtures/enert/dead_proxy_59081.json
```

---

## Scale roadmap (say explicitly)

Not implemented in this pass — document as future platform work:

- Windows service mode for fleet agents
- FastAPI local API (`windows_network_toolkit/platform/api.py`)
- RBAC, fleet aggregation, SIEM export
- Prometheus metrics, signed packaging
- Sysmon/Event Log integration for writer causation

This honesty strengthens senior-level interviews.

---

## Demo script

[three-minute-demo-script.md](three-minute-demo-script.md)

---

## Related

- [classification-model.md](classification-model.md)
- [proof-vs-observation.md](proof-vs-observation.md)
- [architecture/canonical_decision_pipeline.md](architecture/canonical_decision_pipeline.md)
