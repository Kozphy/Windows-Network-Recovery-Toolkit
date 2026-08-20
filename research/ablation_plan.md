# Ablation Plan

The purpose of ablation is to identify which evidence families materially contribute to classification quality and which merely add complexity.

Run the full classifier, then remove exactly one component at a time:

| Ablation | Removed evidence / mechanism | Question |
|---|---|---|
| A1 | WinHTTP evidence | Does cross-stack reconciliation matter? |
| A2 | WinINET evidence | Is the system overly dependent on user proxy state? |
| A3 | listener reachability | Does local-port evidence reduce false positives? |
| A4 | TLS/path evidence | Does path evidence distinguish configuration from transport failures? |
| A5 | proof-tier logic | Does explicit evidence sufficiency improve safe interpretation? |
| A6 | limitations generation | Does the output still satisfy explainability/safety contracts? |

For each ablation, report delta macro-F1, delta false-positive rate, delta critical recall, and changed case IDs.

Ablation results must not be used to rewrite the final evaluation set. Unexpected degradation or improvement belongs in the discussion and error analysis.
