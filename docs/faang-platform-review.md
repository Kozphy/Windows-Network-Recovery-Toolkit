# FAANG Platform Engineering Review Guide

For **platform**, **SRE**, and **reliability** interviewers evaluating engineering depth.

---

## What to evaluate

| Pillar | Evidence in repo |
|--------|------------------|
| Deterministic state machine | `windows_network_toolkit/proxy_state_machine.py` |
| Fixture replay | `proxy-replay` CLI, `tests/test_proxy_state_transitions.py` |
| CI safety contracts | `tests/test_proxy_classifier_safety_contract.py`, `tests/test_policy_safety_contract.py` |
| Hash-chained audit | `src/platform_core/governance/chain_of_custody.py` + tamper tests |
| Typed domain model | `docs/domain-model.md`, Pydantic routes in `backend/technology_risk_routes.py` |
| Read-only API | `GET /trisk/*` — no mutation endpoints |

---

## Architecture choices (interview defense)

1. **CLI-first JSON** — automation-friendly; UI optional  
2. **Full before/after classification** — avoids field-diff false positives (localhost removed ≠ remote proxy)  
3. **Coalescing window** — merges rapid registry sub-events into one transition  
4. **Proof tiers T0–T5** — caps claim strength without telemetry  
5. **Dry-run default** — remediation is preview until typed confirmation  

---

## Demo commands (5 min)

```powershell
pytest -q tests/test_proxy_state_transitions.py tests/test_proxy_classifier_safety_contract.py
python -m windows_network_toolkit proxy-replay --input tests/fixtures/proxy_transitions/proxy_enable_flapping_loop.jsonl
python -m windows_network_toolkit proxy-disable --dry-run --fixture tests/fixtures/enert/dead_proxy_59081.json
```

---

## What we deliberately did not build

- CDN, rate limiting, multi-tenant fleet ingest (roadmap docs only)  
- Autonomous repair agents  
- Malware/EDR classification  

---

## Related

- [state-machine.md](state-machine.md)
- [faang-platform-review.md](faang-platform-review.md) → see [architecture-infographic.md](architecture-infographic.md)
- [adr/ADR-portfolio-positioning.md](adr/ADR-portfolio-positioning.md)
- [api-trisk-examples.md](api-trisk-examples.md)
