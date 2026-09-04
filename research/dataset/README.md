# Research Dataset (public façade)

Research-safe view of the endpoint diagnosis benchmark.

## Canonical storage

| Path | Role |
|------|------|
| [`benchmarks/dataset_v1/`](../../benchmarks/dataset_v1/) | **Canonical** cases (`cases.jsonl`), label schema, provenance |
| `research/dataset/` (this tree) | Public schema, labels export, generators for scale-out |

Do **not** duplicate large fixture bodies here. Generators emit anonymized feature records suitable for ML baselines; they do not invent live enterprise telemetry.

## Privacy / safety

Excluded from this dataset:

- Real usernames, hostnames, emails
- Secrets, tokens, API keys
- Non-anonymized IP identities (fixtures use loopback/`127.0.0.1` only when needed)
- Proprietary enterprise packet captures

Provenance categories are explicit (`synthetic_fixture`, `derived_from_existing_fixture`, …).

## Ground truth

`ground_truth_failure` / `expected_incident_class` are **author-assigned labels independent of detector predictions**. See [`docs/research/data_leakage_controls.md`](../../docs/research/data_leakage_controls.md).

## Reproduce labels export

```powershell
$env:PYTHONPATH = (Get-Location).Path
python -m research.dataset.export_labels
```

## Seedable generator (scale-out scaffolding)

```powershell
python -m research.dataset.generators --seed 42 --count 50 --out research/dataset/processed/synthetic_smoke.jsonl
```

Default CI does **not** require large generated corpora.

## Schema

See [`schema.json`](schema.json) and [`schema.py`](schema.py).
