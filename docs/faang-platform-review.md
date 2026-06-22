# FAANG Platform Engineering Review Guide

For **platform**, **SRE**, and **reliability** interviewers evaluating engineering depth.

---

## What to evaluate

| Pillar | Evidence in repo |
|--------|------------------|
| Deterministic state machine | `windows_network_toolkit/proxy_state_machine.py` |
| Fixture replay | `proxy-replay` CLI, `replay-benchmark`, `tests/test_proxy_state_transitions.py` |
| Classifier evaluation | `classifier-benchmark` offline harness — [classifier-evaluation-report.md](classifier-evaluation-report.md) |
| CI safety contracts | `tests/test_proxy_classifier_safety_contract.py`, `tests/test_policy_safety_contract.py` |
| Hash-chained audit | `src/platform_core/governance/chain_of_custody.py` + tamper tests |
| Human review queue | `src/platform_core/governance/human_review.py` — [human-review-workflow.md](human-review-workflow.md) |
| Fleet simulate | `fleet-simulate` CLI (mixed proxy failures, seeded) |
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

## Failure modes (honest)

| Failure mode | Mitigation in repo |
|--------------|-------------------|
| Classifier drift | `classifier-benchmark` golden fixtures + CI |
| Nondeterministic pipeline output | `replay-benchmark` canonical hash compare |
| False escalation on healthy proxy | Negative cases in benchmark corpus |
| Accusatory narrative in AI text | `explanation_guardrails` + forbidden phrase scan |
| Autonomous remediation | Policy PREVIEW_ONLY + typed confirmation |
| Audit tampering | `verify_chain` on JSONL append log |

---

## 60-second FAANG pitch

> "This is decision infrastructure for developer endpoint reliability: deterministic JSON CLI, fixture-safe CI, policy-gated remediation defaults, and replay benchmarks that prove the pipeline is stable across runs. I'll show dead-proxy classification, preview-only disable, replay-benchmark determinism, and hash-chained audit — the same patterns internal platform teams use before fleet rollout."

---

## Demo commands (5 min)

```powershell
pytest -q tests/test_proxy_state_transitions.py tests/test_proxy_classifier_safety_contract.py
python -m windows_network_toolkit proxy-replay --input tests/fixtures/proxy_transitions/proxy_enable_flapping_loop.jsonl
python -m windows_network_toolkit proxy-disable --dry-run --fixture tests/fixtures/enert/dead_proxy_59081.json
python -m windows_network_toolkit classifier-benchmark --cases examples/evaluation/classifier_benchmark_sample.json --format markdown
python -m windows_network_toolkit replay-benchmark --cases tests/fixtures/evaluation/replay_cases.jsonl
pytest -q tests/platform_core/evaluation tests/platform_core/governance/test_human_review.py tests/platform_core/ai_risk_analyst/test_explanation_guardrails.py
curl -s http://127.0.0.1:8000/trisk/health
```

(FAANG demo path: **replay benchmark** + state machine tests + `/trisk/health` when Docker demo is up.)

---

## What we deliberately did not build

- CDN, rate limiting, multi-tenant fleet ingest (roadmap docs only)  
- Autonomous repair agents  
- Malware/EDR classification  

---

## Related

- [state-machine.md](state-machine.md)
- [classifier-evaluation-report.md](classifier-evaluation-report.md)
- [evidence-replay-benchmark.md](evidence-replay-benchmark.md)
- [human-review-workflow.md](human-review-workflow.md)
- [architecture-infographic.md](architecture-infographic.md)
- [adr/ADR-portfolio-positioning.md](adr/ADR-portfolio-positioning.md)
- [api-trisk-examples.md](api-trisk-examples.md)
