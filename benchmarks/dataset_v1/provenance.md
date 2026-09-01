# Benchmark dataset v1 — provenance

## Purpose

Versioned, deterministic benchmark for research question RQ1 in `RESEARCH.md`:

> Can deterministic, evidence-tiered endpoint diagnosis improve classification quality,
> auditability, safety, and decision reproducibility compared with simpler troubleshooting baselines?

## Source categories

| Category | Description |
|----------|-------------|
| `derived_from_existing_fixture` | Cases adapted from `examples/evaluation/classifier_benchmark_sample.json` and `tests/fixtures/` |
| `synthetic_fixture` | Inline fixtures constructed for controlled edge cases |
| `incomplete_evidence` | Missing probes, listeners, or path evidence |
| `contradictory_evidence` | Conflicting signals across WinINET, listener, and probe layers |
| `adversarial_edge_case` | Misleading health inject or partial state designed to stress baselines |

## Leakage controls

- Expected labels were defined **before** baseline implementation in `experiments/baselines/`.
- A **held-out** split (`split: held_out`) is reserved for reporting; baselines are not tuned on held-out IDs.
- Cases are **not** rewritten after benchmark runs to improve metrics.

## Limitations

- All evidence is **fixture-synthetic** — not live enterprise telemetry.
- Windows-specific proxy/TLS semantics may not generalize to other platforms.
- Proof-tier expectations are ordinal minimums, not probabilistic confidence.

## Hashes

File SHA-256 digests are recorded in `manifest.json` at dataset freeze time.
