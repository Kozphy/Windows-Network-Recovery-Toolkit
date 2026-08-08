# Reproducibility Protocol

The research claims of this repository are valid only when an independent reviewer can reconstruct how a result was produced.

## Required run metadata

Every experiment artifact should record:

- git commit SHA
- classifier/version identifier
- fixture set revision or hash
- Python version
- operating system
- dependency lock/hash when available
- random seed for synthetic fleets
- command line used
- UTC timestamp

## Determinism requirements

For identical code, fixture revision, configuration, and seed:

- classification labels must match
- proof tiers must match
- policy outcomes must match
- machine-readable experiment rows must be stable apart from explicitly excluded timestamps/IDs

A deterministic replay mismatch is a failed research run and should be investigated before publishing aggregate metrics.

## Artifact layout

Recommended generated layout:

```text
research/results/<run-id>/
  manifest.json
  predictions.jsonl
  metrics.json
  confusion_matrix.csv
  ablations.csv
  environment.txt
```

Generated artifacts should distinguish curated fixtures, synthetic fixtures, and any future real-world evidence. Do not merge these categories into one headline number without separate reporting.

## Suggested execution flow

1. run the repository safety-contract tests
2. freeze the evaluated fixture revision
3. execute baseline A
4. execute baseline B
5. execute the full classifier
6. execute ablations
7. compute metrics from saved predictions, not from manually copied counts
8. rerun with the same seed and verify equality
9. record limitations next to reported results

## Research integrity rules

- Never invent or hand-edit benchmark numbers.
- Never describe synthetic fleets as production deployment evidence.
- Keep failed runs when they reveal a methodology defect.
- Version ground-truth corrections.
- Separate exploratory experiments from results used in a report.
- Prefer exact counts when fixture sets are too small for meaningful inferential statistics.
