# Evaluation Plan

Unified evaluation methodology for the Technology Risk & Control Analytics Platform.

Harnesses: `classifier-benchmark`, `replay-benchmark`, `tests/evaluation/test_scenario_matrix_15.py`.

---

## Metrics

| Metric | Command | Target |
|--------|---------|--------|
| Classification accuracy | `python -m windows_network_toolkit classifier-benchmark` | Primary label match on golden set |
| Replay determinism | `python -m windows_network_toolkit replay-benchmark` | Identical outputs on re-run |
| Safety regression | `pytest -q tests/test_policy_safety_contract.py` | Zero destructive bypass |
| Control matrix | `pytest -q tests/evaluation/test_ctrl_matrix_regression.py` | CTRL-001–010 anchored |

---

## 15 Controlled Scenarios

| ID | Description | Expected classification | Proof tier | Policy gate | Pass criteria |
|----|-------------|----------------------|------------|-------------|---------------|
| EV-001 | WinINET proxy enabled, localhost port closed | `DEAD_PROXY_CONFIG` | T2 | PREVIEW | Primary match + limitations |
| EV-002 | WinHTTP direct, WinINET proxy enabled | `WININET_WINHTTP_MISMATCH` | T1–T2 | PREVIEW | Mismatch secondary or primary |
| EV-003 | Known dev proxy owns localhost port | `KNOWN_DEV_PROXY` | T2 | ALLOW | Dev heuristic match |
| EV-004 | Unknown process owns proxy port | `UNKNOWN_LOCAL_PROXY` | T2 | REQUIRE_HUMAN_REVIEW | Low confidence OK |
| EV-005 | Proxy re-enabled after disable | `REVERTER_SUSPECTED` | T2+ | REQUIRE_HUMAN_REVIEW | Timeline pattern |
| EV-006 | Browser TLS fails, curl succeeds | TLS path / `POSSIBLE_MITM_RISK` | T3 | REQUIRE_HUMAN_REVIEW | No MITM_CONFIRMED language |
| EV-007 | PAC file configured | `PAC_CONFIGURED` | T1 | ALLOW | PAC URL present |
| EV-008 | Insufficient permissions | `ERROR_INSUFFICIENT_DATA` | T0 | BLOCK | Confidence ≤ 0.3 |
| EV-009 | Healthy no proxy | `NO_PROXY` | T1 | ALLOW | ProxyEnable=0 |
| EV-010 | Active localhost proxy (dev) | `LOCAL_PROXY_ACTIVE` | T2 | PREVIEW/ALLOW | Listener match |
| EV-011 | Suspicious external proxy | `SUSPICIOUS_PROXY` | T1–T2 | REQUIRE_HUMAN_REVIEW | Remote server |
| EV-012 | Golden dead proxy 59081 | `DEAD_PROXY_CONFIG` | T2 | PREVIEW | Confidence ≥ 0.9 |
| EV-013 | Proxy flapping loop | `REVERTER_SUSPECTED` | T2 | REQUIRE_HUMAN_REVIEW | JSONL replay |
| EV-014 | IPv6 loopback proxy | `DEAD_PROXY_CONFIG` or mismatch | T1–T2 | PREVIEW | Transition fixture |
| EV-015 | Correlation-only listener | Secondary signals only | T1–T2 | PREVIEW | No FINAL_CAUSATION unlock |

Golden file: `tests/fixtures/evaluation/scenarios_15.json`

---

## False Positive / False Negative Notes

- **FP:** Corporate SSL inspection mimics MITM indicators → always emit `limitations[]`
- **FN:** WPAD-only proxy not in WinINET keys → may classify as NO_PROXY
- **FP:** Intentional WinINET/WinHTTP split → mismatch is informational not incident
- **FN:** Reverter outside watch window → missed REVERTER_SUSPECTED

---

## Reproducibility

```powershell
pip install -r requirements.txt
pytest -q tests/evaluation/
python -m windows_network_toolkit classifier-benchmark --cases examples/evaluation/classifier_benchmark_sample.json
python -m windows_network_toolkit replay-benchmark --cases tests/fixtures/evaluation/replay_cases.jsonl
```

Related: [classifier-evaluation-report.md](classifier-evaluation-report.md), [evidence-replay-benchmark.md](evidence-replay-benchmark.md)
