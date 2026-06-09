# SLO Targets (Prototype)

| SLO | Target |
|-----|--------|
| `diagnosis_latency_p95_ms` | < 500ms (fixture replay) |
| `policy_evaluation_p99_ms` | < 50ms |
| `audit_write_success_rate` | 99.9% |
| `replay_certification_success_rate` | 100% on golden fixtures |
| `outcome_recording_success_rate` | 99% |

Measured via `src/platform_core/operability/slo.py` and exposed at `GET /v1/metrics`.
