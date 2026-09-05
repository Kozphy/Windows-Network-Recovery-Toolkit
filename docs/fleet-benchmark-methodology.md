# Fleet benchmark methodology

Offline synthetic benchmark for fleet-scale **portfolio** demonstrations.

The benchmark has one rule that matters more than a large endpoint number: **never present simulated scale as measured performance**. The generated fleet size and the number of timed endpoint-pipeline executions are therefore reported separately.

## Command

```powershell
python -m windows_network_toolkit fleet-benchmark \
  --scenario mixed_proxy_failures \
  --endpoints 1000 \
  --seed 42 \
  --format markdown \
  --out reports/benchmarks/fleet-1000.md
```

`--endpoints 1000` means 1,000 synthetic endpoints are generated. By default, the benchmark times at most 200 endpoint analytics executions. The report exposes both values as `simulated_endpoints` and `measured_endpoints` so a reviewer can see exactly what was exercised.

## Reproducibility manifest

Every v2 summary contains a privacy-safe `environment` object with:

- Python version and implementation
- OS family/release and machine architecture
- CPU count
- process bitness
- commit SHA when supplied by CI (`GITHUB_SHA` / `GIT_COMMIT`)
- whether the run executed under CI

Host names, user names, arbitrary environment variables, IP addresses, and network identifiers are deliberately excluded. The manifest exists to answer **"are these two benchmark runs comparable?"**, not to fingerprint the workstation.

## Scenarios

| Scenario | Intent |
| ---------- | -------- |
| `mixed_proxy_failures` | Weighted production-like mix |
| `dead_localhost_proxy_spike` | Dead proxy concentration |
| `wininet_winhttp_drift` | Stack mismatch drift |
| `known_dev_proxy_noise` | False escalation negative cases |
| `reverter_suspected_loop` | Flapping pattern |
| `tls_path_mismatch` | TLS triage signals (not MITM verdict) |
| `malformed_evidence_burst` | Validation/quarantine stress |
| `duplicate_event_replay` | Duplicate-pressure scenario; production ingest dedupe is **not** measured by this harness |

## Reported metrics

| Metric | Interpretation |
|--------|----------------|
| `simulated_endpoints` | Synthetic fleet size generated for the scenario |
| `measured_endpoints` | Maximum endpoint pipeline executions selected for timing |
| `attempted_analytics` | Measured executions eligible to enter the analytics path after malformed-fixture rejection |
| `completed_measurements` | Analytics executions that completed successfully |
| `execution_failures` | Analytics attempts that raised an exception, including deterministic injected failures |
| `execution_failure_ratio` | Execution failures divided by attempted analytics |
| `latency_p50_ms` / `p95` / `p99` | Local wall-clock latency for one successful endpoint analytics execution |
| `analytics_throughput_eps` | Completed endpoint analytics executions per second during the timed section |
| `analytics_elapsed_ms` | Timed analytics section only |
| `benchmark_wall_clock_ms` | Simulation plus analytics benchmark wall clock |
| classification histogram / unknown ratio | Deterministic output quality indicators |
| malformed rejected | Invalid cases rejected before the analytics path |
| duplicates deduped | `0` with `duplicate_events_deduped_measured=false` until a real ingest/dedupe path is instrumented |
| control PASS / FAIL | Control-test results emitted by successful measured pipeline executions |

## Deterministic failure injection

`run_fleet_benchmark(..., inject_failure_every=N)` intentionally fails every Nth measured analytics attempt. This is a **test hook**, not distributed chaos engineering. It proves that the benchmark separates successful work, malformed input rejection, and execution failures instead of silently dropping failures from latency/throughput reporting.

Example:

```python
from windows_network_toolkit.fleet_benchmark import run_fleet_benchmark

summary = run_fleet_benchmark(
    endpoints=100,
    measurement_cap=100,
    inject_failure_every=10,
)
assert summary["execution_failures"] == 10
assert summary["completed_measurements"] == 90
```

## Regression thresholds

`windows_network_toolkit.benchmark_quality` provides `BenchmarkThresholds` and `evaluate_benchmark_regression`. Thresholds are explicit and opt-in because hardware-dependent latency must not be treated as portable by default.

```python
from windows_network_toolkit.benchmark_quality import (
    BenchmarkThresholds,
    evaluate_benchmark_regression,
)

quality = evaluate_benchmark_regression(
    summary,
    BenchmarkThresholds(
        max_p95_ms=25.0,
        max_p99_ms=40.0,
        min_throughput_eps=100.0,
        max_unknown_ratio=0.02,
        max_execution_failure_ratio=0.0,
    ),
)
assert quality["status"] == "PASS"
```

A team should only pin latency/throughput thresholds after choosing a stable runner, fixture corpus, measurement cap, and warm-up policy. Until then, correctness/failure-accounting gates are more defensible than arbitrary performance numbers.

## Credibility contract

A benchmark report is suitable for an interview only when the presenter can state all of the following:

1. **Environment:** OS, Python version, architecture/CPU count, commit SHA where available.
2. **Scale:** simulated endpoint count and measured endpoint count separately.
3. **Workload:** exact scenario and seed.
4. **Metric boundary:** what the latency timer includes and excludes.
5. **Failure accounting:** completed, rejected, and failed measurements.
6. **Regression policy:** which thresholds are configured and why they are valid for that environment.
7. **Non-claim:** local synthetic results are not production SLA, capacity, availability, or fleet-rollout proof.

Do not extrapolate p95/p99 from 200 measured executions into a claim about 100,000 live endpoints. A production capacity claim requires a real ingest path, concurrency model, deployment topology, persistence layer, load generator, environment capture, repeated runs, and error-budget/SLO analysis.

## Interview interpretation

The value of this harness is not the biggest endpoint number. It demonstrates that the project treats **measurement design as part of system design**: reported scale is auditable, the execution environment is captured, failures are first-class metrics, regression criteria are explicit, synthetic assumptions are visible, and unmeasured behavior is labeled rather than estimated.
