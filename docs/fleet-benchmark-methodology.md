# Fleet benchmark methodology

Offline synthetic benchmark for fleet-scale **portfolio** demonstrations.

## Command

```powershell
python -m windows_network_toolkit fleet-benchmark \
  --scenario mixed_proxy_failures \
  --endpoints 1000 \
  --seed 42 \
  --format markdown \
  --out reports/benchmarks/fleet-1000.md
```

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
| `duplicate_event_replay` | Idempotency stress |

## Reported metrics

- Total events, classification histogram, unknown ratio
- p50/p95/p99 pipeline latency (wall clock)
- Malformed rejected, duplicates deduped
- Control PASS/FAIL counts
- Explicit limitations — not production SLA proof
