# Data Leakage Controls

Controls for the Evidence-Based Endpoint Risk and Decision System research track.

## Rules

1. **Independent labels.** `expected_incident_class` / `ground_truth_*` are authored with the case, never computed from the detector under test.
2. **No label-in-features.** Feature extractors must not include the ground-truth string, taxonomy id, or `case_id` encoding of the class.
3. **Split discipline.** Cases marked `held_out` must not be used to tune rules or train `B_ML`. Development may guide engineering; held-out is for reporting.
4. **Grouped leakage.** Fixtures derived from the same underlying scenario should share a `scenario_id` / family; future ML splits should use grouped splitting when duplicates exist.
5. **Preprocessing fit scope.** Any scaler/encoder for `B_ML` must fit on the training fold only.
6. **Generator isolation.** Synthetic generators choose labels from templates, then emit features — not the reverse. Seed is recorded in `generation_seed`.
7. **No test-set optimization loop.** Do not repeatedly retune against held-out until metrics look good without recording the search.
8. **Audit.** Experiment `metadata.json` records git SHA, seed, manifest version, and dataset digest.

## Known residual risks

- Author overlap between fixtures and B3 rules (overfit) — mitigated by held-out reporting and threats-to-validity disclosure.
- Coarse synthetic generator features may be trivially separable — treat generator smoke as **method plumbing**, not paper headline evidence, until feature richness matches the fixture benchmark.

## Related artifacts

- Dataset: `benchmarks/dataset_v1/`, `research/dataset/`
- Taxonomy: `configs/failure_taxonomy.yaml`
- Runner metadata: `experiments/results/*/metadata.json`
