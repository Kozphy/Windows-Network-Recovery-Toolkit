# Detection Engine

Modular rules in `src/purple_team/detection/`:

| Rule | Intent |
| --- | --- |
| DET-PROXY-001 | Unauthorized proxy enable |
| DET-PROXY-002 | WinHTTP/WinINET mismatch |
| DET-ENDPOINT-001 | Stale/missing/inconsistent endpoint |
| DET-TLS-001 | Synthetic TLS path anomaly (no MITM) |
| DET-BENIGN-001 | Authorized admin control (must not alert) |

Each result explains what changed, why suspicious, evidence, confidence, benign alternative, and recommended action.

Positive and negative tests live in `tests/purple_team/`.
