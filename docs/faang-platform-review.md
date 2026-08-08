# FAANG Platform Engineering Review Guide

For **platform**, **SRE**, and **reliability** interviewers evaluating engineering depth. This is a production-shaped portfolio prototype, not a claim of Google/Microsoft production scale.

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
| Fleet simulation | `fleet-simulate` CLI (mixed proxy failures, seeded) |
| Measurement credibility | `fleet-benchmark` separates simulated from measured scale — [fleet-benchmark-methodology.md](fleet-benchmark-methodology.md) |
| Reproducibility manifest | `benchmark_quality.capture_environment_manifest()` captures environment without host identity |
| Regression guardrails | `BenchmarkThresholds` + `evaluate_benchmark_regression()` provide explicit PASS/FAIL checks |
| Failure accounting | deterministic `inject_failure_every` test hook proves failures are counted, not hidden |
| Typed domain model | `docs/domain-model.md`, Pydantic routes in `backend/technology_risk_routes.py` |
| Read-only API | `GET /trisk/*` — no mutation endpoints |
| Scale migration reasoning | [ADR-008](adr/ADR-008-fleet-scale-100k-endpoints.md) — target architecture, explicit non-claim |

---

## Architecture choices (interview defense)

1. **CLI-first JSON** — automation-friendly; UI optional.
2. **Full before/after classification** — avoids field-diff false positives (localhost removed ≠ remote proxy).
3. **Coalescing window** — merges rapid registry sub-events into one transition.
4. **Proof tiers T0–T5** — caps claim strength without telemetry.
5. **Dry-run default** — remediation is preview until typed confirmation.
6. **Deterministic rules before probabilistic automation** — the system makes governed decisions from explicit evidence contracts; AI is limited to explanation.
7. **Local-first before distributed transport** — JSONL/Postgres are sufficient for the prototype; Kafka/multi-region topology is a migration option triggered by measured requirements, not résumé decoration.
8. **Failure accounting before percentile optics** — a fast p95 is meaningless if failed work silently disappears from the denominator.

---

## Measurement credibility

A reviewer should be able to distinguish three different claims:

| Claim | What the repo can currently support |
|------|-------------------------------------|
| "The simulator generated N endpoints" | Yes — deterministic synthetic workload |
| "The benchmark timed N endpoint pipeline executions" | Yes — explicitly reported as `measured_endpoints` |
| "The deployed system supports N live endpoints at an SLO" | **No** — requires real concurrent ingest, persistence, topology, repeated load/fault testing |

The benchmark reports `simulated_endpoints`, `measured_endpoints`, attempted analytics, completed measurements, explicit execution failures, p50/p95/p99 local latency, throughput for the timed analytics section, and a privacy-safe environment manifest. It does not fabricate deduplication success for the duplicate-pressure scenario.

A benchmark summary is versioned as `fleet-benchmark.v2`. Environment fields include Python version, OS release, machine architecture, CPU count, commit SHA when available, and CI state. Hostname, username, arbitrary environment variables, and network identifiers are deliberately excluded.

Interview-safe wording:

> "I can show deterministic simulation and local measured pipeline performance. I deliberately do not call that production fleet capacity. The benchmark captures the environment, counts failed attempts separately, and can be evaluated against explicit thresholds when the runner is stable. ADR-008 defines what evidence would trigger a distributed redesign."

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
| Benchmark overclaim | Simulated vs measured scale reported separately |
| Silent benchmark failure | attempted/completed/failure counters + deterministic failure injection tests |
| Machine-dependent threshold misuse | latency/throughput thresholds are opt-in and must be tied to a stable runner |
| Premature distributed complexity | Scale components require measurement/SLO trigger in ADR-008 |

---

## Staff-style system design questions

### What happens at 100,000 endpoints?

Do not answer "add Kafka." Start with arrival rate, burst factor, event size, persistence/replay objectives, and tenant boundaries. Measure the simple topology first. If queue age, persistence latency, or replay objectives fail repeatedly, split the bottleneck and re-measure. See [ADR-008](adr/ADR-008-fleet-scale-100k-endpoints.md).

### How do you prevent duplicate remediation?

Evidence delivery can be at-least-once, but governed actions need a stable event/decision identity and an idempotency boundary. Redelivery may recompute a deterministic classification; it must not create a second registry mutation or second approval effect.

### What if classification is wrong?

Classification does not directly authorize mutation. Proof tiers and limitations cap claim strength; policy defaults to preview; risky/accusatory-adjacent cases enter human review; audit/replay preserves the decision trail.

### Why not use an LLM for classification?

The core labels are safety- and audit-relevant. Deterministic rules make fixture replay and regression exact. An LLM may explain already-derived evidence, but it is not the authority for proof, policy, or execution.

### What if the event store is unavailable?

The production design should preserve durable upstream evidence or apply backpressure rather than bypass policy/audit stages. A local demo may fail closed; a distributed design needs WAL/stream retention and explicit recovery objectives.

### What does the hash chain prove?

It provides tamper evidence for log sequence/content after append. It does **not** prove that the original observation was true, that the endpoint was uncompromised, or that an audit opinion is valid.

### How do you know the benchmark is not hiding failures?

The harness separately reports malformed rejection, attempted analytics, completed measurements, execution failures, and injected failures. A deterministic test hook can fail every Nth attempt, and tests assert that the denominator and completed count change correctly. Successful-call latency percentiles therefore remain interpretable without erasing failed work from the report.

### When should a performance regression fail CI?

Only after the runner, fixture corpus, warm-up policy, and measurement cap are stable. Until then, correctness and zero-unexpected-failure gates are portable; arbitrary laptop p95 thresholds are not. `BenchmarkThresholds` therefore leaves latency and throughput unset by default but supports explicit CI thresholds later.

---

## 60-second FAANG pitch

> "This is decision infrastructure for Windows endpoint reliability. I collect deterministic evidence, classify it with explicit proof limits, run control tests, gate remediation behind policy and human review, and preserve replayable audit evidence. The engineering focus is keeping evidence, authority, and side effects separate. The benchmark follows the same discipline: simulated scale and measured scale are separate, the environment is captured, failed work is counted, and regression thresholds are explicit rather than invented."

---

## Demo commands (5 min)

```powershell
pytest -q tests/test_proxy_state_transitions.py tests/test_proxy_classifier_safety_contract.py
python -m windows_network_toolkit proxy-replay --input tests/fixtures/proxy_transitions/proxy_enable_flapping_loop.jsonl
python -m windows_network_toolkit proxy-disable --dry-run --fixture tests/fixtures/enert/dead_proxy_59081.json
python -m windows_network_toolkit classifier-benchmark --cases examples/evaluation/classifier_benchmark_sample.json --format markdown
python -m windows_network_toolkit replay-benchmark --cases tests/fixtures/evaluation/replay_cases.jsonl
python -m windows_network_toolkit fleet-benchmark --scenario mixed_proxy_failures --endpoints 1000 --seed 42 --format markdown
pytest -q tests/platform_core/evaluation/test_fleet_benchmark.py
pytest -q tests/platform_core/governance/test_human_review.py tests/platform_core/ai_risk_analyst/test_explanation_guardrails.py
curl -s http://127.0.0.1:8000/trisk/health
```

During the fleet benchmark, explicitly point out that the generated fleet can exceed the number of timed pipeline executions; then show the execution-environment block and failure counters. This is intentional evidence discipline, not a limitation to hide.

---

## What we deliberately did not build

- A demonstrated 100k-endpoint production deployment.
- A production SLO or availability claim.
- Distributed chaos engineering; the current fault hook is deterministic benchmark instrumentation.
- CDN or multi-region control plane merely for portfolio optics.
- Autonomous repair agents.
- Malware/EDR classification.

---

## Related

- [state-machine.md](state-machine.md)
- [classifier-evaluation-report.md](classifier-evaluation-report.md)
- [evidence-replay-benchmark.md](evidence-replay-benchmark.md)
- [fleet-benchmark-methodology.md](fleet-benchmark-methodology.md)
- [human-review-workflow.md](human-review-workflow.md)
- [architecture-infographic.md](architecture-infographic.md)
- [adr/ADR-008-fleet-scale-100k-endpoints.md](adr/ADR-008-fleet-scale-100k-endpoints.md)
- [adr/ADR-portfolio-positioning.md](adr/ADR-portfolio-positioning.md)
- [api-trisk-examples.md](api-trisk-examples.md)
