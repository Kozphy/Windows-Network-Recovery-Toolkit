# Replay Demo — Deterministic Proxy Transition Classification

Replay applies the **same** state machine and coalescing logic as live `proxy-watch`, without touching the registry.

## Prerequisites

```powershell
pip install -e ".[dev]"
```

## Basic replay

```powershell
python -m windows_network_toolkit proxy-replay --input tests/fixtures/proxy_transitions/proxy_enable_flapping_loop.jsonl
```

**Expected summary fields:**

- `coalesced_event_count` — merged transitions  
- `reverter_loop_detected: true` — for flapping fixture  
- `controls[]` — Big 4 audit controls (PASS/FAIL)  

## Fixture library

| Fixture | Teaches |
|---------|---------|
| `localhost_proxy_removed.json` | Empty ProxyServer ≠ remote proxy |
| `localhost_proxy_disabled_and_removed.json` | Coalesced disable + removal |
| `localhost_to_remote_proxy.json` | Remote transition when after server non-empty |
| `proxy_enable_flapping_loop.jsonl` | Reverter loop (correlation only) |

## Determinism check

```powershell
pytest -q tests/test_proxy_state_transitions.py::test_after_proxy_server_none_is_never_remote_proxy_configured
pytest -q tests/windows_network_toolkit/test_proxy_state_machine.py
```

Same input → same `transition_class`, `event_id`, and `primary_classification`.

## What replay proves

- Classifier is **pure** and **fixture-testable**  
- Coalescing merges rapid sub-events  
- Safety violations are empty for removal fixtures  

## What replay does not prove

- Registry writer identity  
- Live network path on your machine  
- That remediation was applied or stayed sticky  

## Related

- [proxy-state-transitions.md](proxy-state-transitions.md)
- [test-strategy.md](test-strategy.md)
- [interview-demo-3min.md](interview-demo-3min.md)
