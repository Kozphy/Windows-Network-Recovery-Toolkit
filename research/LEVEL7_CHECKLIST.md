# Level 7 Evidence Gate

Level 7 is an evidence threshold, not a feature-count threshold.

## Executable evaluation
- [x] Temporal past-to-future holdout runner
- [x] Simple supervised baselines
- [x] Optional probability calibration
- [x] Bootstrap uncertainty interval
- [x] Feature-group ablation support
- [x] Machine-readable result artifacts

## Required before claiming Level 7 complete
- [ ] Versioned labeled telemetry dataset with documented provenance
- [ ] Rules-only baseline evaluated on the same temporal holdout
- [ ] False-positive rate reported explicitly
- [ ] Calibration error / reliability analysis
- [ ] Full-vs-baseline paired statistical comparison
- [ ] Failure taxonomy populated from observed errors
- [ ] Reproduction command verified in a clean environment / CI
- [ ] Dataset card filled with actual collection window and labeling procedure
- [ ] Leakage review completed
- [ ] Limitations and threats-to-validity reviewed against generated results

## Claim discipline

Synthetic/demo data may validate software execution, but it must not be presented as evidence of production detection quality or enterprise effectiveness. ML output remains decision evidence; remediation requires policy/human governance.
