# Threats to Validity — Research Benchmark v1

This document accompanies `RESEARCH.md` and the reproducible benchmark in `benchmarks/dataset_v1/`.

## Internal validity

**Fixture design may favor components we implemented.** Cases derive from existing test fixtures and classifier benchmark samples. Labels were frozen before baseline coding, but fixture authors shared the same codebase as the classifier.

**Mitigation:** Held-out split (5/22 cases), adversarial/contradictory cases, and reporting where B3 **loses** to simpler baselines on specific cases.

## External validity

**Windows proxy/TLS scenarios may not generalize.** All evidence is synthetic JSON — not live WinINET registry reads, enterprise PAC files, or fleet-scale telemetry.

**Conclusion scope:** Results apply to *benchmark dataset v1 under controlled fixtures*, not production MTTR or fleet-wide incident rates.

## Construct validity

**Classification accuracy ≠ operational usefulness.** Operators may care about time-to-diagnosis, false remediation previews, or audit committee readability — not macro F1 alone.

**Mitigation:** Separate evidence-quality and safety/governance metrics; error taxonomy; explicit limitations in every output.

## Dataset leakage

**Fixtures were created during platform development.** Several cases map 1:1 to existing `tests/fixtures/` files used in unit tests.

**Mitigation:** `provenance.md` documents categories; held-out IDs are not used for tuning; we do not rewrite labels post-hoc to improve B3.

## Human factors

**Automated metrics cannot prove auditor/operator satisfaction.** Policy-match rates are synthetic comparisons to expected fixture posture, not user studies.

## Synthetic-data limitation

Without real enterprise evidence we **cannot** claim:

- Production-validated detection rates
- Guaranteed safer remediation in live environments
- Statistical superiority over IT runbooks in the field

We **can** claim (with artifact citations):

- On dataset v1, B3 achieved higher macro F1 than B0/B2 under the defined protocol
- Ablation A2/A3 reduce accuracy vs full system
- Deterministic replay agreement for B3 on repeated runs

## Reproducibility threats

- Python/platform version drift → recorded in `experiments/results/*/metadata.json`
- Dependency updates → pin via `pyproject.toml`; CI uses Python 3.11

See also: [statistical-methods.md](statistical-methods.md) · [research/technical_report.md](../research/technical_report.md)
