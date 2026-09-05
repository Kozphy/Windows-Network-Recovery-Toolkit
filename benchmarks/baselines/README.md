# Baselines

Reference implementations: `experiments/baselines/`

| ID | Module | Uses |
|----|--------|------|
| B0 | `b0_connectivity.py` | Probe/connectivity signals only |
| B1 | `b1_flat_rules.py` | Flat if/else rules, no proof tiers |
| B2 | `b2_single_signal.py` | WinINET `proxy_state` only |
| B3 | `b3_full_platform.py` | Classifier + proof tier + policy path |

All baselines share benchmark dataset v1 and output schema in `experiments/contract.py`.
