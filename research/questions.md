# Proxy Drift Research Questions

## Scope

This research track evaluates whether the toolkit's richer temporal and cross-source evidence improves proxy-drift classification beyond simpler rules. It is deliberately narrower than the full platform and does not make malware, compromise, or enterprise-generalization claims.

## RQ1 — Detection quality

**Question:** Does temporal and cross-source configuration context reduce false-positive proxy-drift detections compared with static rule-based detection under controlled Windows endpoint scenarios?

**H1:** The context-aware classifier will reduce false-positive rate by at least 20% relative to a static rule baseline while preserving recall within 5 percentage points.

## RQ2 — Detection latency

**Question:** What is the trade-off between observation interval and mean time to detect a genuine proxy-drift event?

**H2:** Shorter observation intervals reduce MTTD, but the marginal gain below a practical threshold will be smaller than the increase in collection overhead.

## RQ3 — Component contribution

**Question:** Which evidence dimensions contribute most to classification quality?

**H3:** Temporal state and agreement/disagreement across WinINET and WinHTTP will account for more of the performance gain than DNS/TLS context alone.

## Primary outcomes

- Precision
- Recall
- F1
- False-positive rate (FPR)
- False-negative rate (FNR)
- Mean time to detect (MTTD), when temporal traces are available
- 95% bootstrap confidence intervals for key metric deltas

## Non-claims

- Controlled or synthetic scenarios are not presented as representative of all enterprise fleets.
- Confidence scores in the current platform are not treated as calibrated probabilities unless a separate calibration experiment is performed.
- Statistical significance alone will not be interpreted as operational usefulness.
- No result will be generalized beyond the tested Windows versions, policies, and scenario families without external validation.
