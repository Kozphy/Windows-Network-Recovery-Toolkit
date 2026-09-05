# Phase 1 — Interaction Effects

Measures whether combined fault factors produce **non-additive** outcomes on controlled 2×2 factorial fixtures.

## Research question

> Does `Effect(X1 + X2)` differ from `Effect(X1) + Effect(X2)`?

Model (linear probability / severity):

```text
Y = β0 + β1·X1 + β2·X2 + β3·(X1 × X2)
```

Interaction contrast: **Y11 − Y10 − Y01 + Y00**

## Experiments

| ID | Factors |
|----|---------|
| `proxy_x_firewall` | proxy fault × firewall filtering |
| `proxy_x_tls` | proxy fault × TLS/path mismatch |
| `wininet_x_winhttp` | WinINET enabled × WinHTTP direct access |
| `proxy_x_listener` | proxy enabled × listener present |
| `dns_x_proxy` | DNS fault × proxy fault |
| `listener_x_process` | Listener present × trusted process attribution |

Each cell has **3 replicates** (n=12 per experiment).

## Run

```powershell
$env:PYTHONPATH = (Get-Location).Path
python -m research.interactions
```

## Outputs

```text
experiments/results/interaction_effects.csv
experiments/results/interaction_cases.jsonl
experiments/results/interaction_summary.json
docs/research/interaction_effects.md
```

## Discipline

- Ground-truth severity is **designed** for interaction contrast — not field probability.
- Bootstrap CIs are exploratory; do not claim significance without adequate data.
- Platform classifier outcomes are reported separately from designed outcomes.
