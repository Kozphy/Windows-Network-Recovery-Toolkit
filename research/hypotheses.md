# Hypotheses

## H1
Multi-source / multi-rule purple detection will improve F1 compared with baseline_0 (no detection) and baseline_1 (static ProxyEnable threshold) on the fixture suite.

## H2
Independent post-remediation verification will identify failures that command-success checks incorrectly classify as recovered.

## H3
Context-aware suppression (`authorized=true`) will reduce false positives on benign-admin scenarios without materially reducing recall on unauthorized drift scenarios.

## Evaluation note
Hypotheses are tested via `python -m src.purple_team baselines` and ablation presets — not by fabricating metrics.
