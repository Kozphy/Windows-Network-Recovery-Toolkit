# Executable research benchmark

This directory implements a deterministic, fixture-only evaluation layer for the Technology Risk
& Control Analytics Platform. It turns the protocol in [`../RESEARCH.md`](../RESEARCH.md) into
executable evidence; it does not manufacture performance claims.

## What is implemented

```text
experiments/
  manifest.json                  frozen dataset inventory and SHA-256
  configs/
    benchmark-v1.json            B0-B3 run configuration
    ablations-v1.json            component-ablation configuration
  baselines/
    connectivity.py              B0: reachability only
    flat_rules.py                B1: first-match flat rules
    single_signal.py             B2: WinINET configuration only
    full_platform.py             B3: real analytics/proof/policy adapter
  scripts/
    run_benchmark.py             raw B0-B3 predictions + replay checks
    run_ablations.py             raw ablation predictions + replay checks
    compute_metrics.py           derived CSV/JSON metrics
    build_report.py              derived Markdown report
  results/                       machine-generated run artifacts
```

The synthetic case files live under `tests/fixtures/research/v1/` with `development`, `held_out`,
and `adversarial` splits. The split boundaries and canonical file digests are frozen in
`manifest.json`.

## Reproduce the benchmark

Run from the repository root:

```powershell
python experiments/scripts/run_benchmark.py --config experiments/configs/benchmark-v1.json
python experiments/scripts/run_ablations.py --config experiments/configs/ablations-v1.json
python experiments/scripts/compute_metrics.py
python experiments/scripts/build_report.py
```

The first two commands produce raw JSONL predictions and run manifests under
`experiments/results/`. The third command derives `benchmarks/results.csv`,
`benchmarks/confusion_matrix.csv`, `benchmarks/ablations.csv`, `benchmarks/metrics.json`, and
`benchmarks/environment.json`. The final command renders `benchmarks/benchmark_report.md` from
those generated values.

No metric cell is maintained by hand.

## Frozen case contract

Each `research_case.v1` file contains:

- a stable `case_id` and split;
- an explicit `synthetic: true` provenance marker;
- input-only `signals`;
- predeclared expected classification, minimum proof tier, and policy posture.

The adapters receive the case object, but B3 consumes only `signals`; a regression test changes
the expected label and verifies that B3 output does not change.

`experiments/manifest.json` stores the case count, canonical dataset SHA-256, and per-file digests.
The runners fail closed when a fixture changes without a matching manifest update. Modify v1 only
with an explicit versioning decision; prefer creating v2 for substantive label or signal changes.

## Baselines

### B0 — connectivity only

Uses only `connectivity_ok`. It represents a host-reachability check that cannot distinguish
proxy, application, and TLS paths.

### B1 — flat rules

Uses the supplied observations in a deterministic first-match rule table. It assigns no evidence
strength and performs no contradiction aggregation. This is a credible simplified comparator,
not an intentionally broken straw baseline.

### B2 — single signal

Uses only WinINET enabled/server configuration. It abstains or emits a coarse label when listener
and path evidence would be required.

### B3 — full platform adapter

Calls the repository's real `normalize_events_from_fixture`, `classify_incident_from_events`, and
`resolve_proof_tier` implementations, then maps the platform's policy recommendation to a
non-executing benchmark posture. It is read-only and performs no registry, firewall, adapter, or
process change.

This adapter deliberately preserves current classifier misses. It does not read expected labels
or patch predictions to match the fixture.

## Raw prediction contract

Each JSONL row contains at least:

```json
{
  "case_id": "DEV-001",
  "split": "development",
  "model_or_baseline": "B3_full_platform",
  "expected_class": "DEAD_PROXY_CONFIG",
  "predicted_class": "DEAD_PROXY_CONFIG",
  "proof_tier": "T2_RUNTIME_CORROBORATION",
  "limitations": [],
  "policy_decision": "PREVIEW_ONLY",
  "runtime_ms": 0.0,
  "deterministic_digest": "<sha256>",
  "replay_mismatch": false
}
```

`runtime_ms` is measured and intentionally excluded from the deterministic digest. Predictions,
proof tiers, policy postures, limitations, and supporting signals are replayed at least twice.
Any mismatch is recorded as an experiment failure.

## Metrics

`compute_metrics.py` calculates, by split and overall:

- exact accuracy;
- macro precision, recall, and F1;
- unsupported-classification and abstention rates;
- explicit-limitation and proof-minimum coverage;
- policy-match and unsafe-proposal rates;
- replay mismatch counts;
- descriptive mean runtime.

Macro metrics use the expected label set in the evaluated group. Small fixture counts are always
reported alongside rates.

## Ablations

The executable v1 ablations are:

- A1 — remove proof tiers;
- A2 — remove listener/process observations;
- A3 — remove direct/proxy path observations;
- A4 — remove `limitations[]`;
- A5 — remove the policy gate in a serialized counterfactual only;
- A7 — replace cross-signal aggregation with B1 flat rules.

A5 can mark an unsafe proposal in output, but it never calls remediation code. A6 hash-chain
removal is not included in classification metrics: tamper detection requires a separate audit
experiment and would be misleading to simulate as a classification row.

## Safety and interpretation boundaries

1. All cases are fictional, sanitized fixtures; there is no production telemetry.
2. `held_out` enforces repository workflow separation but is not an independently sourced set.
3. A classification is triage guidance, not a malware, compromise, or intent verdict.
4. Proof tier does not grant execution authority.
5. No adapter executes remediation; policy-gate removal is output-only.
6. Fixture accuracy does not establish MTTR improvement or external validity.
7. Failed cases and negative ablation results remain in the generated artifacts.

## Tests

```powershell
pytest -q tests/experiments/test_research_benchmark.py
ruff check experiments tests/experiments
```

The tests verify dataset freezing, label isolation, replay determinism, safety boundaries, and
end-to-end artifact derivation.
