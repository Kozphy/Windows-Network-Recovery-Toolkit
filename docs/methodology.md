# Methodology

## Primary research question

Can an evidence-based endpoint risk and decision system detect and classify Windows endpoint/network failure conditions more accurately and reliably than simpler baselines on a fixed synthetic/fixture benchmark?

Formal RQ1–RQ3: [`research/research_questions.md`](research/research_questions.md).

## Baselines (shared harness)

| ID | Role | Brief alias |
|----|------|-------------|
| B0 | Connectivity-only | A (weak / naive) |
| B1 | Flat rules | A (rule-based) |
| B2 | Single-signal heuristic | B (heuristic scoring) |
| B_ML | Bernoulli NB on anonymized fixture features | C (classical ML) |
| B3 | Full evidence-tiered platform | D (proposed system) |

**Do not renumber published B3 CSVs.** Classical ML is `B_ML`, not a replacement for B3.

## Protocol

1. Load `benchmarks/dataset_v1` (or smoke subset).
2. Run each baseline through `experiments.runner`.
3. Score against independent `expected_incident_class`.
4. Export metrics, confusion matrices, bootstrap CIs, ablations (B3), runtime CSV.
5. Record git SHA, seed, dataset digests in `metadata.json`.

## ML split rule

`B_ML` **fits only on `split=development`** cases loaded from the dataset directory, then predicts on the evaluation case list. Held-out labels are never used for training.

## Latency / remediation semantics

- **Wall-clock runtime** of fixture prediction is measured (batch ms).
- **Live detection latency / MTTR** are **not applicable** on fixtures — recorded as `not_applicable`.
- Remediation “success” in this harness is **policy/posture match**, not live registry repair.

## Reproduce

```powershell
$env:PYTHONPATH = (Get-Location).Path
make research-smoke
# or
python -m experiments.run_benchmark --manifest experiments/manifests/v1.json
```

Architecture map: [`research/research_architecture.md`](research/research_architecture.md).
