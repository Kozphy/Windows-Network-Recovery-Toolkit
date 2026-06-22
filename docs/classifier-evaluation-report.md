# Classifier evaluation report

**Deterministic classifier evaluation harness for endpoint reliability evidence.**

This is not AI benchmark research. It measures offline fixture replay of the incident classifier and policy posture — without live Windows registry access.

## Metrics

| Metric | Meaning |
|--------|---------|
| `total_cases` | Benchmark cases executed |
| `exact_primary_classification_match_rate` | Predicted primary class equals expected |
| `secondary_signal_match_rate` | Overlap of secondary signals |
| `unsafe_recommendation_rate` | Outputs containing forbidden security-product language |
| `limitation_coverage_rate` | Required limitation phrases present |
| `policy_gate_correctness_rate` | Policy mode matches expected |
| `false_escalation_count` | Stricter risk/policy than expected (non-ambiguous cases) |
| `false_downgrade_count` | Looser risk/policy than expected (non-ambiguous cases) |
| `ambiguous_case_count` | Cases where ambiguity is explicitly allowed |

## Run

```powershell
python -m windows_network_toolkit classifier-benchmark \
  --cases examples/evaluation/classifier_benchmark_sample.json \
  --format markdown
```

## Governance boundary

- Classification is not accusation.
- Management information only — not a formal audit opinion.
- Does not prove malware or MITM.
