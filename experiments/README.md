# Experiments

Reproducible evaluation workflow for the Technology Risk & Control Analytics Platform. Research questions: [`../RESEARCH.md`](../RESEARCH.md).

## Frozen experimental contract (v1)

```text
experiments/
  manifest.schema.json       # JSON schema for manifests
  manifests/v1.json          # Default B0–B3 benchmark manifest
  configs/v1.json            # Smoke config (8-case limit)
  contract.py                # ExperimentManifest + ExperimentRunRecord
  raw_results/<run_id>/      # predictions.csv, run_records.csv
  processed_results/<run_id>/ # metrics.csv, latency.csv
  results/<run_id>/          # Full artifact bundle + latest/
```

**Run:**

```powershell
python -m experiments.run_benchmark --manifest experiments/manifests/v1.json
python -m experiments.run_all   # benchmark + datasets export + research docs + interactions
```

Every run records: `experiment_id`, git SHA, dataset version, manifest version, seed, per-scenario predictions, and bootstrap CIs in `benchmarks/bootstrap_ci.csv`.

**Visualize:**

```powershell
python -m experiments.viz --open   # HTML dashboard + Power BI CSV export
```

See [`../analytics/powerbi/research/README.md`](../analytics/powerbi/research/README.md) for Power BI Desktop import.

See [`../REPRODUCING.md`](../REPRODUCING.md) for full reproduction steps.

---

## Directory contract (legacy reference)

```text
experiments/
  README.md
  manifest.json              # dataset + code/config identifiers
  configs/                   # frozen experiment configurations
  baselines/                 # baseline implementations/configs
  scripts/                   # runners and metric-generation scripts
  results/                   # machine-generated raw outputs
  reports/                   # derived tables/figures, never hand-edited metrics
```

## Required experiment families

### E1 — Classification benchmark

Compare:

- B0 connectivity-only,
- B1 flat rules,
- B2 single-signal diagnostics,
- B3 full evidence-tiered platform.

Minimum outputs:

- per-case predicted class,
- expected class,
- proof tier,
- limitations,
- policy decision,
- runtime,
- deterministic digest.

### E2 — Replay determinism

Run the same fixture set repeatedly and verify agreement for:

- classification,
- proof tier,
- policy result,
- content digest,
- audit-chain verification.

Any mismatch is a failed experiment unless nondeterminism was explicitly designed, seeded, and documented.

### E3 — Safety / policy benchmark

Construct cases that include:

- permitted read-only actions,
- preview-only remediation,
- approval-required actions,
- blocked unsafe actions.

Measure false allows, false blocks, missing approvals, and policy mismatches.

### E4 — Ablation study

Evaluate the contribution of major components by removing them one at a time. Follow the ablations defined in [`../RESEARCH.md`](../RESEARCH.md).

### E5 — Audit tamper experiment

Create a valid audit chain, mutate or remove a row in a copied artifact, and verify that chain validation reports the failure. Preserve both original and tampered fixtures.

## Manifest

Every published run should record a manifest similar to:

```json
{
  "schema_version": "experiment_manifest.v1",
  "git_commit": "<sha>",
  "dataset": {
    "name": "proxy-risk-benchmark",
    "version": "v1",
    "sha256": "<digest>",
    "case_count": 0
  },
  "python_version": "<version>",
  "seed": 42,
  "config": "configs/full-platform-v1.json"
}
```

Do not fill placeholder values with guessed numbers.

## Result schema

Prefer JSONL for raw case-level output. A minimum record should look like:

```json
{
  "case_id": "CASE-001",
  "expected_class": "DEAD_PROXY_CONFIG",
  "predicted_class": "DEAD_PROXY_CONFIG",
  "proof_tier": "T4",
  "limitations": [],
  "policy_decision": "PREVIEW_ONLY",
  "runtime_ms": 0,
  "digest": "<sha256>"
}
```

Additional evidence fields are encouraged when they help reconstruct the decision.

## Metric generation

Derived metrics should be produced from raw outputs by script. The reporting step should generate at least:

```text
benchmarks/results.csv
benchmarks/confusion_matrix.csv
benchmarks/ablations.csv
```

Recommended metric columns include:

- model_or_baseline,
- case_count,
- accuracy,
- macro_precision,
- macro_recall,
- macro_f1,
- unsupported_classification_rate,
- abstention_rate,
- unsafe_action_proposal_rate,
- replay_mismatch_count.

## Held-out evaluation

Separate development fixtures from held-out evaluation fixtures. If a case was used to design or debug a rule, it should not be presented as independent evidence of generalization.

Suggested organization:

```text
fixtures/research/
  development/
  held_out/
  adversarial/
```

Keep the split stable for a benchmark version.

## Adversarial / ambiguous cases

Include cases designed to challenge overconfident classification:

- proxy configured but listener intermittently available,
- WinINET and WinHTTP disagree,
- TLS succeeds on one path and fails on another,
- listener exists but process ownership is unavailable,
- evidence timestamp ordering is incomplete,
- contradictory evidence from different collection windows,
- healthy endpoint with unusual-but-valid configuration.

The desired behavior may be abstention or a lower proof tier rather than a forced diagnosis.

## Reproduction goal

The end state should support a command such as:

```powershell
python experiments/scripts/run_benchmark.py --config experiments/configs/full-platform-v1.json
python experiments/scripts/build_report.py --results experiments/results --out benchmarks
```

Those scripts do not yet exist merely because this documentation names them. Add them only when backed by real executable implementations and tests.

## Reporting rules

1. Never manually edit generated metric cells to improve presentation.
2. Report case counts alongside rates.
3. Preserve failed cases.
4. Record the exact Git commit used.
5. Separate development-set and held-out-set results.
6. Do not call fixture-only results a production benchmark.
7. Do not infer MTTR reduction from classification accuracy.
8. Link every headline claim to a generated result artifact.

## Completion criteria

This experiment layer becomes reviewer-ready when a clean checkout can execute the benchmark from documented fixtures and regenerate all published tables without manual intervention.
