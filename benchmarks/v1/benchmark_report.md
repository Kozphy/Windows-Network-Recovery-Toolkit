# Proxy Risk Benchmark v1

Fixture-only comparison of connectivity, flat-rule, health-only, and full evidence-tiered diagnosis.

| Baseline | Cases | Accuracy | Macro F1 | Unsupported | Unsafe action proposals |
|---|---:|---:|---:|---:|---:|
| B0_CONNECTIVITY | 12 | 0.250 | 0.129 | 0.417 | 0.000 |
| B1_FLAT_RULES | 12 | 0.500 | 0.359 | 0.917 | 0.167 |
| B2_HEALTH_STATUS | 12 | 0.417 | 0.384 | 0.333 | 0.000 |
| B3_FULL_PLATFORM | 12 | 1.000 | 1.000 | 0.000 | 0.000 |

## Reproduce

```powershell
python experiments/scripts/run_benchmark.py --config experiments/configs/proxy-risk-v1.json --out experiments/results/v1
python experiments/scripts/build_report.py --results experiments/results/v1 --out benchmarks/v1
```

## Claim boundary

These results describe this versioned fixture set only. They do not establish enterprise accuracy, MTTR reduction, malware detection, or autonomous-remediation safety.
