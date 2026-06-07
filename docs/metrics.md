# Metrics and benchmark vocabulary

Deterministic counters for portfolio demos, dashboards, and `GET /platform/metrics`. Values are synthesized from append-only JSONL — missing files yield **zero**, not errors.

---

## Core KPIs

| Metric | Source | Meaning |
|--------|--------|---------|
| **diagnosis_latency_ms** | CLI/API timing wrappers | Wall time for fixture or read-only diagnose path |
| **audit_events_count** | `audit.jsonl`, `decision_audit.jsonl` tails | Append-only rows written |
| **policy_decision_distribution** | Reasoning / platform events | Count of ALLOW vs PREVIEW vs BLOCK |
| **replay_success_rate** | `platform_core.replay.runner` | `1 - parse_errors/total_events` on fixture corpus |
| **unsafe_action_block_count** | Remediation executions with `result=blocked` | Forbidden/high/manual denials |
| **proof_confirmed_count** | Proof payloads with `status=CONFIRMED` | Scoped causal checks passed |
| **proof_rejected_count** | `status=REJECTED` | Causal story contradicted |
| **proof_inconclusive_count** | `INCONCLUSIVE` or `UNPROVEN` | Needs more telemetry or evidence |

---

## Demo scenario catalog

Nine deterministic scenarios in [`demo_data/manifest.json`](../demo_data/manifest.json):

| Scenario id | Fixture pointer |
|-------------|-----------------|
| `healthy_endpoint` | `tests/fixtures/features_healthy_signals.json` |
| `proxy_drift` | `tests/fixtures/features_proxy_issue.json` |
| `localhost_proxy_stale_listener` | `tests/fixtures/platform/proxy_loopback_enabled.json` |
| `dns_failure` | `tests/fixtures/features_dns_issue.json` |
| `tcp443_blocked` | `tests/fixtures/tcp_failure.json` |
| `https_browser_path_failure` | `tests/fixtures/https_failure.json` |
| `remediation_not_sticky` | See proxy soak / investigate docs |
| `suspected_proxy_hijack_unproven` | `tests/fixtures/platform/suspicious_proxy_change.json` |
| `confirmed_proxy_bypass_contrast` | `tests/fixtures/platform/endpoint_browser_only_failure.json` |

---

## Collecting metrics locally

```powershell
# Platform KPI merge (requires backend data dir or empty defaults)
curl -s -H "X-Operator-Role: admin" http://127.0.0.1:8000/platform/metrics

# Replay determinism on inline fixture
python -c "from platform_core.replay.runner import summarize_inline; import json; e=[{'schema_version':'1','signals':{'remediation_action':'inspect_proxy','simulated_operator_role':'admin'}}]; print(json.dumps(summarize_inline(e).__dict__))"
```

Future: `tools/benchmark_demo.py` → `reports/benchmark_demo.md` (roadmap item).

---

## Extended platform counters

See prior sections in this file for `proxy_changes_total`, `attribution_confidence_avg`, incident clustering fields — populated when agents append rows to `platform_signals.jsonl`.

Implementation: `platform_core/metrics.py`, `platform_core/toolkit_metrics.py`.

---

## What metrics do **not** claim

- Not real-time fleet SLIs without agent ingest.
- Not calibrated MTTR — prototype counters only.
- Not proof rates without telemetry fixtures — label proof counts explicitly in dashboards.
