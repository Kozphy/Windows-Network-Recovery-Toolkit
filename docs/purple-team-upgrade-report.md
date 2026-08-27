# Purple Team Upgrade Report

## Before

Primarily a **Blue Team** Windows endpoint reliability / technology-risk toolkit:

- Fixture diagnostics and classifiers
- Policy-gated remediation (dry-run default)
- Hash-chained custody
- Classifier/replay benchmarks

**Missing:** unified simulate→detect→verify→measure orchestrator, scenario schema with mandatory rollback, modular DET-* rules with FP controls, confusion-matrix purple metrics, ablation/baselines, research layer, portfolio framing for control validation.

## Major architectural changes

1. Added `src/purple_team/` lifecycle orchestrator (state machine + safety gate).
2. Added typed scenario YAML under `scenarios/` (reject incomplete cleanup / remote / prod).
3. Added normalized telemetry + provenance hashes.
4. Added modular detection rules with positive/negative tests.
5. Separated recommendation vs execution; independent verification invariant.
6. Added benchmark / baselines / ablation / error analysis (computed, not fabricated).
7. Added tamper-evident evidence bundles.
8. Added research docs + purple architecture/threat/safety docs.
9. CI smoke: `tests/purple_team` + fixture benchmark + baselines.

## Why they matter

Portfolio signal shifts from “I can run security tools” to:

> We safely reproduce security-relevant conditions, observe telemetry, evaluate whether controls detect them, measure false positives and detection latency, remediate safely (fixture/lab), independently verify recovery, and preserve auditable evidence.

## Implemented controls

| Control | Mechanism |
|---|---|
| Deny by default | `evaluate_safety` |
| Dry-run preview | `validate` / `dry_run_preview` |
| Schema safety | cleanup required; remote/prod forbidden |
| FP measurement | `benign-admin-001` |
| Verification integrity | failed verify ⇒ not recovered |
| Evidence integrity | chained hashes + verify CLI |
| CI safety | fixture-only purple jobs |

## Benchmark methodology

See `research/evaluation_protocol.md`. Reproduce:

```bash
python -m src.purple_team benchmark --no-evidence --json
python -m src.purple_team baselines
```

## Measured results

Run the commands above — **do not hard-code numbers in docs**. CI stores `reports/purple_benchmark.json` artifacts.

## Known limitations

- Fixture lab ≠ production SOC / fleet MTTD.
- Purple remediation mutates fixture state only; live WinINET remains under existing confirmation tokens.
- Custody/bundles are tamper-evident, not WORM.
- MITRE mappings are optional and conservative.

## Next research questions

See `research/questions.md` (RQ1–RQ5) and `research/hypotheses.md` (H1–H3).
