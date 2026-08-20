# Reproducibility Contract

A reported result must be tied to immutable inputs and an identifiable code revision.

## Record for every evaluation

- repository commit SHA
- Python version
- OS and architecture
- dependency lock/manifest hash when available
- fixture manifest with SHA-256 per file
- configuration hash
- seed
- command executed
- normalized result JSON
- metrics JSON

## Determinism check

Run the frozen evaluation 10 times using identical inputs. Strip explicitly non-deterministic metadata such as timestamps before comparison. The normalized classification output must be byte-identical.

## Artifact layout

```text
research/results/<run-id>/
├── manifest.json
├── fixture_hashes.json
├── normalized_predictions.json
├── metrics.json
├── errors.json
└── environment.txt
```

## Reproduction failure

If a result cannot be reproduced from its recorded commit and manifest, mark it `NON_REPRODUCIBLE` and do not use it as portfolio evidence until the cause is explained.
