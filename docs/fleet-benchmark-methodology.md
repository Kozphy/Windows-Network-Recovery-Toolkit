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

## Scenarios

| Scenario | Intent |
|----------|--------|
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
| `completed_measurements` | Timed executions that completed successfully |
| `latency_p50_ms` / `p95` / `p99` | Local wall-clock latency for one endpoint analytics execution |
| `analytics_throughput_eps` | Completed endpoint analytics executions per second during the timed section |
| `analytics_elapsed_ms` | Timed analytics section only |
| `benchmark_wall_clock_ms` | Simulation plus analytics benchmark wall clock |
| classification histogram / unknown ratio | Deterministic output quality indicators |
| malformed rejected | Invalid cases rejected by the harness |
| duplicates deduped | `0` with `duplicate_events_deduped_measured=false` until a real ingest/dedupe path is instrumented |
| control PASS / FAIL | Control-test results emitted by measured pipeline executions |

## Credibility contract

A benchmark report is suitable for an interview only when the presenter can state all of the following:

1. **Environment:** OS, Python version, CPU, RAM, commit SHA.
2. **Scale:** simulated endpoint count and measured endpoint count separately.
3. **Workload:** exact scenario and seed.
4. **Metric boundary:** what the latency timer includes and excludes.
5. **Failure accounting:** completed, rejected, and failed measurements.
6. **Non-claim:** local synthetic results are not production SLA, capacity, availability, or fleet-rollout proof.

Do not extrapolate p95/p99 from 200 measured executions into a claim about 100,000 live endpoints. A production capacity claim requires a real ingest path, concurrency model, deployment topology, persistence layer, load generator, environment capture, repeated runs, and error-budget/SLO analysis.

## Interview interpretation

The value of this harness is not the biggest endpoint number. It demonstrates that the project treats **measurement design as part of system design**: reported scale is auditable, synthetic assumptions are explicit, and unmeasured behavior is labeled rather than estimated.
