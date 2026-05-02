# Test strategy — Endpoint Reliability Platform

This document describes how we keep regressions deterministic, offline-safe, and aligned with reliability goals. Tests must never execute repair binaries, mutate the Windows registry, require elevation, depend on unmanaged external services, or touch the beginner `.bat` toolkit as part of assertions.

## Scope and layers

- **Pure unit**: policy gates, remediation registry lookups, replay counters, privacy helpers, Pydantic event validation.
- **Integration (in-process)** event bus reads over ephemeral JSONL under `tmp_path`.
- **Thin smoke**: subprocess `python -m src …` / `python -m failure_system --help` with `PYTHONPATH` pointed at this repo root; **`--repo-root` to a disposable directory** whenever `diagnose` would persist logs or snapshots so the real checkout is untouched.

Manual or hosted E2E (FastAPI servers, dashboards) is optional and out-of-band for CI safety.

## Fixtures and mocking

Normalized platform fixtures live under `tests/fixtures/platform/`. Feature vectors for the classic CLI live under `tests/fixtures/features_*.json`. Prefer explicit `PYTHONPATH=<repo>` for module smoke passes so editable installs do not hide import regressions.

## Safety Regression Matrix

| Concern | How we regress it | Typical test anchor |
|--------|-------------------|---------------------|
| No live repair during tests | No assertions spawn `scripts/*.bat`; API tests use dry-run routes or offline policy only | Repository-wide avoidance (see `tests/test_safety_regression.py`) |
| High-risk / forbidden blocks | Firewall and arbitrary-command paths deny preview/execute appropriately | `test_firewall_manual_only_blocks_*`, `test_arbitrary_command_*` |
| Default deny | Unknown actions yield `unknown_action`; viewer role blocks preview | `test_unknown_action_default_deny` |
| Confirmation before execute semantics | Operators may preview only; admins need typed phrase at route boundary; registry phrase for proxy is `RUN_PROXY_RESET` | `test_policy_preview_operator_*`, `test_proxy_reset_accepts_*` |
| Event schema privacy | `endpoint_id_hash` must be hex digest (24–128 chars); sham “proof” attribution rejected without tamper-evident metadata | `test_normalized_event_rejects_*`, `test_audit_row_symmetric_*` |
| JSONL resilience | Bad lines accumulate parse errors without killing the reader | `test_event_bus_skips_bad_jsonl_*` |
| Replay purity | Inline replay uses in-memory aggregates only (no filesystem) | `test_replay_summarize_inline_does_not_open_*` |
| Replay drift detection | Embedded `policy_decision` mismatches re-evaluated gates | `test_replay_detects_drifting_*` |
| Registry backward compatibility | Aliases flatten to identical legacy meta (`reset_firewall`, `arbitrary_command`) | `test_remediation_aliases_share_*` |
| Attribution modesty | Heuristic providers never emit `confidence=proof` | `test_attribution_process_heuristic_never_claims_proof` |
| Classic CLI continuity | Fixture `diagnose` run with isolated `--repo-root` exits 0 | `test_smoke_python_m_src_fixture_diagnose_isolated_repo` |
| Network State Manager | Snapshot/diff/policy/report/audit/evidence parsing with fakes only; CLI list smoke uses `--repo-root` temp | `tests/test_network_state_manager.py` |
| Proxy change attribution | Pure parse/diff/score/audit/CSV import + inventory graceful failure; no live PowerShell registry | `tests/test_proxy_change_attribution.py` |
| Failure system entry | `-m failure_system --help` exits 0 | `test_smoke_failure_system_help_exits_clean` |

Run the focused suite:

```powershell
pytest tests/test_safety_regression.py tests/test_platform_faang_upgrade.py -q
```

Run the full project suite from the repo root as your environment allows.
