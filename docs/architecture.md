# Architecture: Endpoint Reliability Platform

> **Start here:** [START_HERE.md](START_HERE.md) · **Canonical core:** `src/platform_core/`

## Package map (2026 consolidation)

| Package | Status | Purpose |
|---------|--------|---------|
| `src/platform_core/` | **Canonical** | Evidence tiers, policy, audit chain, replay, outcomes |
| `windows_network_toolkit/` | **Mainline facade** | CLI, collectors, bad-gateway diagnose, reports |
| `src/proxy_guard/` | **Mainline probes** | Live Windows proxy collection + remediation previews |
| `backend/canonical_routes.py` | **Canonical API** | `/v1/*` decision pipeline |
| `backend/platform_routes.py` | Legacy | `/platform/*` JSONL ingest |
| `platform_core/` (root) | Legacy ops | Fleet, SRE, remediation registry — shim to canonical |
| `src/platform/` | MDP | Multi-domain fixture demos |
| `labs/` | Experimental | Not production mainline |
| `frontend/` | Demo UI | Next.js operator console |

Local-first **endpoint reliability and security observability** for Windows proxy/browser-path failures.

> **Observation ≠ Correlation ≠ Proof** — policy is orthogonal. See [evidence_model.md](evidence_model.md) and [policy_model.md](policy_model.md).

## Canonical pipeline

```text
probes (WinINET, WinHTTP, DNS, ping, browser path)
  → event normalization (JSONL)
  → evidence fusion (OBSERVED_ONLY … FINAL_CAUSATION)
  → reasoning engine (hypothesis ranking, ordinal confidence)
  → policy engine (ALLOW_OBSERVE … BLOCK_DESTRUCTIVE)
  → remediation preview (dry-run default)
  → append-only audit
  → replay engine (deterministic)
  → API / dashboard / Prometheus metrics
```

For the Failure Knowledge System (FailureBlocks), see [architecture_failure_knowledge.md](architecture_failure_knowledge.md).

---

## System map (modules)

| Path | Layer | Role |
| --- | --- | --- |
| `scripts/` | Control (beginner) | Batch diagnose/repair with prompts — preserved |
| `src/` | Observation + CLI | `python -m src` collectors, proxy guard, live scoring |
| `platform_core/reasoning/` | Inference + policy API | Re-exports event-state models; epistemic caps |
| `platform_core/reasoning_engine.py` | Inference + policy | Pure `run_reasoning()` — no host I/O |
| `platform_core/reasoning_audit.py` | Replay | Recompute from stored observations |
| `platform_core/event_store.py` | Audit | `logs/events.jsonl`, `logs/decisions.jsonl`, `logs/remediation_previews.jsonl` |
| `platform_core/policy/` + `policy_v2.py` | Policy | ALLOW / PREVIEW / BLOCK + `reason_codes` |
| `proxy_guard/`, `src/proxy_guard/` | Observation | WinINET drift, listener correlation |
| `failure_system/` | Knowledge plane | FailureBlocks (read-only probes) |
| `backend/` | API | `/platform/health`, `/metrics`, `/replay/{run_id}` |
| `frontend/` | Dashboard | Incident views (extend timeline from JSONL) |
| `endpoint_agent/` | Observation | Observe-only cycles — no auto-repair |
| `order_flow_simulator/` | Demo / portfolio | Order lifecycle FSM — event sourcing teaching artifact |

---

## Layered pipeline (network reliability)

```text
┌─────────────┐   ┌──────────────┐   ┌─────────────┐   ┌─────────────┐
│ Observation │ → │ Event + State│ → │ Hypothesis  │ → │ Proof (opt) │
│  collectors │   │  transitions │   │  + impact   │   │  contrast   │
└─────────────┘   └──────────────┘   └─────────────┘   └─────────────┘
       │                  │                  │                  │
       v                  v                  v                  v
 append-only        evidence tree      ordinal confidence   CONFIRMED/
 JSONL events       rejected alts      (not probability)    INCONCLUSIVE
       │                  │                  │                  │
       └──────────────────┴──────────────────┴──────────────────┘
                                    v
                          ┌─────────────────┐
                          │ PolicyDecision  │
                          │ ALLOW/PREVIEW/  │
                          │ BLOCK + codes   │
                          └─────────────────┘
                                    v
                          ┌─────────────────┐
                          │ Remediation     │
                          │ preview only    │
                          │ (dry-run def.)  │
                          └─────────────────┘
```

### Layer contracts

| Layer | May claim | Must not claim |
| --- | --- | --- |
| **Observation** | Registry value at T, probe OK/FAIL | Root cause, writer PID proof |
| **Inference** | Ranked hypothesis, state label | Certainty, malware |
| **Proof** | Narrow check CONFIRMED/REJECTED | Whole-system security |
| **Policy** | ALLOW safe-tier with confirmation | Auto-execute destructive work |

---

## Event-state models (`platform_core/reasoning_models.py`)

| Model | Purpose |
| --- | --- |
| `Observation` | Measured fact |
| `EndpointEvent` | Normalized event from observations |
| `StateTransition` | `from_state` → `to_state` + rule_id |
| `EvidenceNode` / `EvidenceTree` | Accepted + rejected alternatives |
| `ProofResult` | Targeted check outcome |
| `ReliabilityImpact` | Ordinal impact ranking |
| `PolicyDecision` | Tri-state + `reason_codes` + `blocked_actions` |
| `ReasoningRun` | Full replayable bundle |

Public import surface: `platform_core.reasoning` (thin package).

---

## Append-only audit (dual write, backward compatible)

| File | Content | Legacy mirror |
| --- | --- | --- |
| `logs/events.jsonl` | Observation/event timeline rows | — |
| `logs/decisions.jsonl` | Policy + hypothesis decisions | `logs/decision_runs.jsonl` (`live_run_audit_v1`) |
| `logs/remediation_previews.jsonl` | Preview catalog rows | `logs/repair_audit.jsonl` (mutations) |
| `platform_data/reasoning_runs.jsonl` | Platform API reasoning | — |

Readers that only know `decision_runs.jsonl` continue to work. New tooling may prefer unified `decisions.jsonl`.

---

## Replay (no live probes)

| Entry | Behavior |
| --- | --- |
| `python -m src replay <run_id>` | Re-score `live_run_audit_v1` observations |
| `platform_core.reasoning_audit.replay_reasoning_record` | Platform reasoning rows |
| `GET /platform/replay/{run_id}` | Stored diagnosis replay |
| `platform_core.event_store.replay_timeline` | Merge events + decisions for one `run_id` |

---

## Order-flow simulator (trading-infra pattern)

Not a trading system — a **reliability demo** for:

- event sourcing
- invalid transition detection
- latency measurement
- append-only audit

```powershell
python -m order_flow_simulator run --scenario happy_path
python -m order_flow_simulator run --scenario invalid_cancel
```

Audit: `logs/order_flow_audit.jsonl`

---

## Safety invariants (architecture-level)

- No destructive auto-repair from API or agent.
- Dry-run default on execute paths.
- Allowlist-only remediation registry.
- Listener correlation ≠ registry writer proof.
- High confidence + unproven proof → **PREVIEW**, not ALLOW.

---

## Related docs

- [event_state_reasoning_platform.md](event_state_reasoning_platform.md)
- [policy_engine.md](policy_engine.md)
- [replay_model.md](replay_model.md) *(if present)*
- [demo_script.md](demo_script.md)
