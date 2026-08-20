# Baselines

## B0 — Always healthy

Predict no proxy drift for every case. This exposes class imbalance and prevents accuracy from being misread as useful performance.

## B1 — WinINET only

Use WinINET proxy configuration as the sole decision input. Ignore WinHTTP state, listener/path evidence, TLS evidence, and cross-source reconciliation.

## B2 — WinHTTP only

Use WinHTTP proxy configuration as the sole decision input.

## B3 — Configuration mismatch heuristic

Flag drift whenever WinINET and WinHTTP effective proxy settings disagree. Do not use listener reachability or TLS/path evidence.

## B4 — Full deterministic classifier

Use the repository's declared multi-source evidence pipeline and state-machine logic. This is the candidate system, not a baseline.

## Fair-comparison rules

- identical frozen fixtures
- identical class labels
- no post-hoc threshold tuning on final evaluation data
- identical exclusion policy
- report per-class results, not only aggregate scores
- preserve safety/non-claim boundaries for every system
