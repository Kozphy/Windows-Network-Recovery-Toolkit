# Synthetic research benchmark report

- Benchmark version: `synthetic-proxy-risk-v1`
- Dataset version: `v1`
- Synthetic case count: **12**
- Dataset SHA-256: `bfc3e9e003f32e4b113cfc55e700c795dd7de60f54269e5b52b5caa09c7f18ea`
- Source commit: `d77daa0da49c30f0ce9e4a6355a798fc69208215`
- Replay mismatch count: **0**

> These are executed fixture results, not production telemetry, an external validation set, or evidence of population-level performance.

## All synthetic splits

| adapter | cases | accuracy | macro F1 | unsupported | policy match | replay mismatches |
|---|---:|---:|---:|---:|---:|---:|
| B0_connectivity_only | 12 | 16.7% | 7.6% | 0.0% | 50.0% | 0 |
| B1_flat_rules | 12 | 100.0% | 100.0% | 8.3% | 100.0% | 0 |
| B2_single_signal | 12 | 16.7% | 10.9% | 25.0% | 41.7% | 0 |
| B3_full_platform | 12 | 83.3% | 81.8% | 0.0% | 91.7% | 0 |

## Held-out synthetic split

| adapter | cases | accuracy | macro F1 | proof minimum met | unsafe proposals |
|---|---:|---:|---:|---:|---:|
| B0_connectivity_only | 4 | 0.0% | 0.0% | 0.0% | 0.0% |
| B1_flat_rules | 4 | 100.0% | 100.0% | 0.0% | 0.0% |
| B2_single_signal | 4 | 25.0% | 10.0% | 0.0% | 0.0% |
| B3_full_platform | 4 | 100.0% | 100.0% | 100.0% | 0.0% |

## Ablations across all synthetic splits

| ablation | macro F1 | delta vs full | limitations present | unsafe proposals |
|---|---:|---:|---:|---:|
| A1_without_proof_tiers | 81.8% | +0.000 | 100.0% | 0.0% |
| A2_without_listener_evidence | 61.2% | -0.206 | 100.0% | 0.0% |
| A3_without_tls_path_evidence | 36.4% | -0.455 | 100.0% | 0.0% |
| A4_without_limitations | 81.8% | +0.000 | 0.0% | 0.0% |
| A5_without_policy_gate | 81.8% | +0.000 | 100.0% | 50.0% |
| A7_without_cross_signal_aggregation | 100.0% | +0.182 | 100.0% | 0.0% |
| full | 81.8% | +0.000 | 100.0% | 0.0% |

## Interpretation boundaries

- Results compare deterministic adapters on repository-authored synthetic fixtures only.
- The `held_out` directory enforces workflow separation but is not an independent dataset.
- Accuracy does not establish operational usefulness, MTTR improvement, or external validity.
- The policy-gate ablation serializes counterfactual proposals; it never executes them.
- Raw predictions and long-form confusion counts remain the authoritative evidence.

## Reproduction

```powershell
python experiments/scripts/run_benchmark.py --config experiments/configs/benchmark-v1.json
python experiments/scripts/run_ablations.py --config experiments/configs/ablations-v1.json
python experiments/scripts/compute_metrics.py
python experiments/scripts/build_report.py
```
