# Experiments

This directory defines the reproducible evaluation workflow for the Technology Risk & Control Analytics Platform.

The experiments are intended to answer research questions from [`../RESEARCH.md`](../RESEARCH.md). They must not be used to manufacture impressive metrics. Raw outputs, failures, and negative results are part of the evidence.

## Directory contract

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

The proxy-risk v1 vertical slice supports:

```powershell
python experiments/scripts/run_benchmark.py --config experiments/configs/proxy-risk-v1.json --out experiments/results/v1
python experiments/scripts/build_report.py --results experiments/results/v1 --out benchmarks/v1
```

The runner is fixture-only and does not read or mutate live Windows state. It validates
the case contract in `experiments/schemas/proxy-risk-case-v1.schema.json`, rejects duplicate
case IDs and split-directory drift, executes B0–B3 twice to check deterministic replay,
and records the Git SHA, dataset digest, configuration digest, environment, and raw output
digest. The report builder refuses to aggregate raw results whose digest no longer matches
the manifest.

Current v1 scope is deliberately narrow: endpoint proxy-state, listener, path-health, and
WinINET/WinHTTP mismatch evidence. ML/LLM comparisons and human operator studies remain
future work; they must not be inferred from this fixture-only benchmark.

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
