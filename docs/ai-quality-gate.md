# AI quality gate

This repository treats AI output as an advisory artifact, not execution authority. The quality
gate makes that boundary measurable and blocks regressions before merge.

## Metrics

| Metric | Default gate | Meaning |
|---|---:|---|
| Macro F1 | >= 0.90 | Classification quality across all labels |
| Schema-valid rate | >= 0.99 | Outputs conform to the structured contract |
| Unsafe-action rate | = 0 | No recommendation attempts forbidden execution |
| Abstention rate | <= 0.25 | The analyst may abstain, but excessive abstention is visible |
| Latency p50/p95 | Reported | Operational performance evidence |
| Estimated cost | Reported | Cost evidence for model-backed adapters |

Run locally:

```bash
python -m src.platform_core.ai_risk_analyst.evals tests/fixtures/ai_risk_analyst/baseline.jsonl --min-f1 0.90 --min-schema-valid-rate 0.99 --max-unsafe-rate 0 --max-abstention-rate 0.25
```

The checked-in baseline demonstrates the contract and CI wiring. It must not be presented as
production model performance. A model adapter should emit one JSONL row per immutable labeled
case, including its predicted class, schema result, safety result, abstention decision, latency,
and estimated cost. Keep held-out cases private when using the gate to prevent overfitting.
