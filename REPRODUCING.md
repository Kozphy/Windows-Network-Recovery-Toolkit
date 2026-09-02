# Reproducing Research Benchmarks

This guide takes a reviewer from **clone → benchmark artifacts** with minimal manual steps.

## Requirements

| Item | Version |
|------|---------|
| OS | Windows 10/11, Linux, or macOS (fixtures are OS-agnostic) |
| Python | 3.11+ (CI uses 3.11) |
| PowerShell | 5.1+ (Windows) or pwsh 7+ |
| Privileges | **None** for default reproduction (read-only fixtures) |
| Network | Optional (no live probes in benchmark mode) |

## Safety

- Default benchmark path uses **fixture-only** evaluation — no registry or proxy mutation.
- Remediation is **not executed** during benchmarks.
- Live Windows changes require explicit CLI flags and typed confirmation tokens elsewhere in the platform.

## One-command reproduction

```powershell
$env:PYTHONPATH = (Get-Location).Path
./scripts/reproduce.ps1
```

Or:

```powershell
pip install -e ".[dev]"
make research
```

## What gets generated

```text
experiments/results/<run_id>/          # timestamped run
experiments/results/latest/            # symlink/copy of key tables
experiments/raw_results/<run_id>/      # predictions + run_records
experiments/processed_results/<run_id>/  # metrics + latency placeholder
benchmarks/results.csv
benchmarks/bootstrap_ci.csv
benchmarks/ablations.csv
benchmarks/error_analysis.csv
benchmarks/reports/research_dashboard.html
analytics/powerbi/research/data/
datasets/v1/scenarios.jsonl
docs/research/TECHNICAL_REPORT.md
docs/research/FAILURE_ANALYSIS.md
docs/research/CLAIMS_EVIDENCE_MATRIX.md
benchmarks/reports/research_dashboard.html   # HTML charts (browser)
analytics/powerbi/research/data/             # Power BI CSV tables
experiments/results/interaction_*.csv  # Phase 1 interaction effects
```

## Visualization

**HTML dashboard (no Power BI license):**

```powershell
python -m experiments.viz --open
# → benchmarks/reports/research_dashboard.html
```

**Power BI Desktop:** import CSVs from `analytics/powerbi/research/data/` per [analytics/powerbi/research/README.md](analytics/powerbi/research/README.md).

## Manual steps (equivalent)

```powershell
$env:PYTHONPATH = (Get-Location).Path
python -m experiments.run_benchmark --manifest experiments/manifests/v1.json
python -m research.interactions
```

Smoke (CI-fast):

```powershell
python -m experiments.run_benchmark --smoke --manifest experiments/configs/v1.json
pytest -q tests/experiments tests/research/interactions
```

## Random seed

- Default seed: **42** (recorded in `metadata.json` and manifest)
- Bootstrap: **1000** iterations (200 in smoke config)

## Known limitations

- **Latency metrics** are `not_applicable` — fixture replay has no wall-clock detection/recovery timing.
- **Recovery success** is posture-match only, not live apply/verify.
- Dataset v1 is **synthetic/replayed** — not enterprise field validation.
- Results on Python 3.14 locally may differ in metadata only; metrics should match with same seed.

## Verify reproducibility

```powershell
pytest -q tests/experiments tests/research/interactions
```

Check `reproducibility_metrics.csv` for B3 digest agreement (target: 100% on fixtures).

## Git traceability

Every run records:

- `git_sha` in `metadata.json`
- `dataset_hashes` in manifest
- `experiment_manifest` block with `manifest_version`

Do not hand-edit CSV metrics; regenerate via `make research`.
