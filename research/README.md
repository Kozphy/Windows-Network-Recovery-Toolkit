# Research Track — Proxy Drift Benchmark

This directory turns the existing engineering platform into a reproducible research testbed. The goal is not to make the repository look academic; it is to test whether the platform's richer evidence model produces measurable gains over simpler approaches.

## Start here

1. Read [`questions.md`](questions.md) for RQ1–RQ3 and falsifiable hypotheses.
2. Read [`protocol.md`](protocol.md) before changing benchmark logic.
3. Review [`datasets/schema.md`](datasets/schema.md) before adding scenarios.
4. Run the example benchmark:

```bash
python research/experiments/evaluate_binary.py \
  --input research/datasets/example.jsonl \
  --methods naive static context
```

Expected example output demonstrates the mechanics only; it is **not** evidence for H1–H3.

## Research maturity ladder

- [x] Research questions and explicit hypotheses
- [x] Frozen benchmark protocol v1
- [x] Dataset schema with provenance classes
- [x] Reproducible binary metric evaluator
- [ ] Implement B0 naive baseline against canonical fixture inputs
- [ ] Implement B1 frozen static-rule baseline
- [ ] Adapt current context-aware classifier into P1 benchmark adapter
- [ ] Build a larger frozen evaluation manifest
- [ ] Add stratified bootstrap confidence intervals
- [ ] Add MTTD trace evaluator
- [ ] Add ablation switches/adapters
- [ ] Add error taxonomy output for FP/FN cases
- [ ] Run controlled Windows experiments
- [ ] Add sanitized real-world evidence where defensible
- [ ] Write results and threats-to-validity sections
- [ ] Produce paper-style manuscript only after results exist

## Important boundary

Do not write a paper that claims the proposed method is better before the baselines and frozen evaluation set exist. The manuscript is the final reporting layer, not the starting point.

## Industry interpretation

The same artifacts can be reviewed as an engineering decision package:

- hypothesis → proposed operational change
- baseline → current/simple implementation
- evaluation metrics → reliability/risk KPIs
- ablation → component value analysis
- error analysis → incident/failure taxonomy
- reproducibility → CI/reviewer repeatability
- threats to validity → deployment and governance boundaries
