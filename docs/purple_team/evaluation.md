# Evaluation

See `research/evaluation_protocol.md` and `research/benchmark_design.md`.

```bash
python -m src.purple_team benchmark --no-evidence --json
python -m src.purple_team baselines
python -m src.purple_team benchmark --ablation minus_proxy_rule --no-evidence
```

Metrics are derived from scenario executions. Do not paste fabricated percentages into docs.
