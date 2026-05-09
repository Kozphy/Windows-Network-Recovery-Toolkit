# Event-State Reasoning Upgrade

## A. Executive Summary

The Endpoint Reliability Platform is being extended from a diagnostics toolkit into a deterministic
event/state reasoning platform. The upgrade keeps the existing local-first safety model and adds a
replayable reasoning chain:

```text
Observation
-> Event
-> State Transition
-> Hypothesis Ranking
-> Confidence / Impact
-> Evidence Tree
-> Optional Proof Result
-> Policy Decision
-> Append-only Audit / Replay
-> Human-readable Explanation
```

The LLM boundary remains strict: language models may translate structured evidence, but the
structured reasoner remains the source of truth.

## B. Current System Map

| Area | Current role | Core runtime path | Remain unchanged | Extension point | Do not touch |
| --- | --- | --- | --- | --- | --- |
| `scripts/` | Beginner `.bat` and PowerShell workflows for proxy, DNS, firewall, and repair preview. | Optional operator path. | Keep command names and familiar beginner flows. | Add references to new reasoning reports only. | Do not remove or silently make scripts more aggressive. |
| `src/` | `python -m src` CLI for diagnosis, proxy guard, proof checks, replay, and repair previews. | Main local CLI runtime. | Preserve current commands and output fields. | Add optional reasoning output beside existing live diagnosis payloads. | Do not break `diagnose`, `diagnose-live`, `preview`, or proxy commands. |
| `failure_system/` | FailureBlock generation, safe probes, output contracts. | Secondary local knowledge path. | Keep FailureBlock schema stable. | Map FailureBlocks into `Observation` and `EndpointEvent`. | Do not turn probe logic into remediation logic. |
| `platform_core/` | Pydantic platform models, policy, storage, metrics, replay helpers. | Core platform domain layer. | Preserve current model and policy APIs. | New event/state reasoning models and audit records. | Do not weaken policy gates. |
| `backend/` | FastAPI `/platform/*` routes, local dashboard backend, safe remediation preview/execute. | Optional HTTP runtime. | Keep no arbitrary shell from API. | Add read-only reasoning endpoints later. | Do not accept free-form shell or unsafe mutations. |
| `frontend/` | Next.js dashboard for platform health, metrics, events, incidents. | Optional UI runtime. | Keep existing dashboard pages. | Add state path and evidence tree views. | Do not add repair buttons that bypass policy. |
| `endpoint_agent/` | Observe-only endpoint collection and optional ingest client. | Optional scheduled observe path. | Keep observe-only semantics. | Emit observations/events to platform data. | Do not execute repairs from the agent. |
| `evidence/` | Conservative attribution adapters for Sysmon, Procmon, ETW-style sources. | Optional enrichment layer. | Keep heuristic/proof separation. | Feed evidence nodes and rejected alternatives. | Do not overclaim registry writer identity. |
| `tests/` | Offline regression and safety tests. | CI/runtime confidence path. | Keep safety tests. | Add reasoning, replay, policy, and evidence-tree tests. | Do not commit generated caches. |

## C. Target Architecture

```text
Collectors / Fixtures / Replay
  |
  v
Observation model
  |
  v
Signal normalization
  |
  v
EndpointEvent detection
  |
  v
StateTransition inference
  |
  v
FailureScenario registry and hypothesis ranking
  |
  +--> EvidenceTree: observed / inferred / proof / rejected / uncertain
  |
  +--> ProofResult: NOT_RUN / CONFIRMED / REJECTED / INCONCLUSIVE
  |
  +--> ReliabilityImpact: severity x scope x confidence x duration
  |
  v
PolicyDecision: ALLOW / PREVIEW / BLOCK
  |
  v
ReasoningRun JSONL audit
  |
  +--> Replay without re-probing
  |
  v
Diagnosis-to-text renderer
```

## D. Data Model Proposal

Implemented in `platform_core/reasoning_models.py`.

| Model | Purpose |
| --- | --- |
| `Observation` | Raw or normalized fact from collector, fixture, or replay. |
| `EndpointEvent` | Event derived from one or more observations. |
| `EndpointState` | Named state in a scenario path. |
| `StateTransition` | Rule-driven transition between states. |
| `FailureScenario` | Reusable state machine with event rules and alternatives. |
| `EvidenceNode` | Tree node for observed, inferred, proof, or rejected evidence. |
| `EvidenceTree` | Accepted hypothesis, state path, reasons, rejected alternatives, uncertainty. |
| `ProofResult` | Optional proof outcome from targeted read-only checks. |
| `ReliabilityImpact` | Explainable impact ranking. |
| `PolicyDecision` | Reasoning-aware policy result. |
| `ReasoningRun` | Full replayable record of the run. |

Confidence fields are ordinal ranking scores, not calibrated probabilities.

## E. Failure Scenario Registry

Implemented in `platform_core/failure_scenarios.py`.

Primary scenario: `browser_proxy_path_regression`.

States:

```text
healthy_browser_path
proxy_drift_detected
browser_path_failure_suspected
proxy_path_failure_confirmed
remediation_preview_ready
resolved
unresolved
```

Key rules:

| Rule | Condition | Transition |
| --- | --- | --- |
| `proxy_drift` | `wininet_proxy_changed` or `wininet_proxy_enabled` or `localhost_proxy_detected` | `healthy_browser_path -> proxy_drift_detected` |
| `browser_path_suspected` | `ping_ok + dns_ok + tcp443_ok + browser_https_failed + wininet_proxy_enabled` | `proxy_drift_detected -> browser_path_failure_suspected` |
| `proxy_path_confirmed` | `proxy_bypass_succeeded + proxied_path_failed` | `browser_path_failure_suspected -> proxy_path_failure_confirmed` |
| `preview_ready` | `policy_preview_allowed` | `proxy_path_failure_confirmed -> remediation_preview_ready` |

Rejected alternatives:

- `total_network_outage`
- `dns_only_failure`
- `tcp_blocked`
- `upstream_isp_issue`
- `certificate_tls_issue`

## F. Evidence Tree Example

```json
{
  "accepted_hypothesis": "browser_proxy_path_regression",
  "state_path": [
    "healthy_browser_path",
    "proxy_drift_detected",
    "browser_path_failure_suspected",
    "proxy_path_failure_confirmed"
  ],
  "accepted_because": [
    "ping_ok",
    "dns_ok",
    "tcp443_ok",
    "browser_https_failed",
    "wininet_proxy_enabled",
    "proxy_bypass_succeeded",
    "proxied_path_failed"
  ],
  "rejected_alternatives": [
    {
      "hypothesis": "total_network_outage",
      "reason": "ping/dns/tcp checks succeeded"
    },
    {
      "hypothesis": "dns_only_failure",
      "reason": "dns resolution succeeded"
    }
  ],
  "proof_status": "CONFIRMED",
  "policy_decision": "PREVIEW",
  "limitations": [
    "Listener/process correlation does not prove registry writer identity.",
    "Registry writer proof requires Sysmon/EventLog/Procmon-style telemetry."
  ]
}
```

## G. Reliability Impact Score

Implemented in `platform_core/impact_score.py`.

```text
impact_score = severity_weight x scope_weight x confidence x duration_weight
```

The score is explainable and ordinal. It is not a probability and not a financial loss model.

Example:

```text
scope = browser_and_dev_tools
severity = high
confidence = 0.86
duration = unknown
impact = high reliability degradation
```

## H. Policy Upgrade

Implemented in `platform_core/reasoning_engine.evaluate_reasoning_policy`.

Inputs:

- hypothesis
- state transition
- evidence level
- proof status
- confidence
- trust / conflicting signals
- reliability impact
- requested remediation action

Outcomes:

- `ALLOW`
- `PREVIEW`
- `BLOCK`

Rules:

- Unproven high confidence remains `PREVIEW`.
- Confirmed proof plus safe action can move to `ALLOW` only when typed confirmation is present.
- Destructive or manual-only actions remain `BLOCK`.
- Conflicting signals downgrade to `PREVIEW`.
- Registry changes require explicit typed confirmation.
- Firewall reset, adapter disable, process kill, and arbitrary shell remain blocked/manual-only.
- High or critical **impact** without confirmed proof forces `outcome = "PREVIEW"` and appends `high_impact_requires_confirmed_proof_before_execute` to `reason_codes`. This is defense-in-depth: even if the ALLOW gate were widened in the future, an unproven high/critical impact path cannot escalate to execute authority.
- Critical **impact** without high trust (CONFIRMED proof, no conflicting signals) forces `outcome = "PREVIEW"` and appends `critical_impact_requires_high_trust_for_execute_authority`.
- Unproven hypothesis (`proof_result.status != "CONFIRMED"`) forces `outcome = "PREVIEW"` and appends `unproven_high_confidence_is_not_execute_authority`. Each guardrail is an independent gate, not just an annotation.

## I. Audit and Replay

Implemented in `platform_core/reasoning_audit.py`.

Append-only records store:

- raw observations
- normalized signals
- detected events
- state transitions
- hypothesis ranking
- evidence tree
- proof result
- policy decision
- recommended next test
- remediation preview
- limitations
- version metadata

Replay recomputes state transition, hypothesis ranking, policy decision, and explanation from the
stored record without probing the machine.

## J. Diagnosis to Text

Implemented in `platform_core/diagnosis_text.py`.

The renderer accepts only structured `ReasoningRun` data. An optional LLM may rewrite this output,
but must not add observations, attribution, proof, or remediation claims.

Example summary:

```text
The endpoint reasoning engine selected browser_proxy_path_regression. State path:
healthy_browser_path -> proxy_drift_detected -> browser_path_failure_suspected ->
proxy_path_failure_confirmed. Proof status is CONFIRMED; policy outcome is PREVIEW.
```

## K. Implementation Plan

Phase 1:

- Add reasoning models.
- Add failure scenario registry.
- Add evidence tree helpers.
- No current CLI/API behavior change.

Phase 2:

- Convert existing diagnosis outputs into observations and events.
- Add evidence tree to JSON output while keeping old fields.

Phase 3:

- Add impact scoring.
- Feed impact into reasoning-aware policy.
- Add regression tests.

Phase 4:

- Persist reasoning runs to append-only JSONL.
- Add replay parity checks.
- Add dashboard state path/evidence tree view.

Phase 5:

- Add Diagnosis-to-Text UI copy from structured evidence only.
- Optional LLM rewrite can operate only on the structured summary.

## L. Files Added / Modified

Added:

- `platform_core/reasoning_models.py`
- `platform_core/failure_scenarios.py`
- `platform_core/evidence_tree.py`
- `platform_core/impact_score.py`
- `platform_core/reasoning_engine.py`
- `platform_core/reasoning_audit.py`
- `platform_core/diagnosis_text.py`
- `tests/test_reasoning_models.py`
- `tests/test_failure_scenarios.py`
- `tests/test_policy_reasoning.py`
- `tests/test_replay_reasoning.py`
- `docs/event_state_reasoning_platform.md`

Modified:

- `platform_core/__init__.py`
- `.gitignore` to keep test source visible

## M. Test Plan

Regression coverage proves:

- Observations become endpoint events.
- Events produce expected state transitions.
- Proxy-path scenario ranks above alternatives when signals match.
- Proof confirmation upgrades evidence but does not bypass confirmation boundaries.
- Unproven high confidence remains `PREVIEW`.
- Conflicting signals downgrade policy.
- Evidence tree contains accepted and rejected hypotheses.
- Replay produces the same policy decision from stored audit data.
- High-risk actions remain blocked.

## N. Safety Review

This upgrade is read-only and deterministic. It does not:

- run arbitrary shell
- disable adapters
- reset firewall
- kill processes
- change registry values
- delete certificates
- use an LLM as diagnosis source of truth

The reasoner can recommend preview or allow safe-tier action only through existing confirmation
boundaries. It preserves the principle that heuristic attribution is not proof.

## O. Interview-Ready Summary

The platform now models endpoint reliability like a risk reasoning system: raw observations become
events, events move endpoint state, state paths rank competing hypotheses, proof checks strengthen
or reject specific causal stories, impact scoring prioritizes user-facing degradation, and policy
gates decide whether the system may allow, preview, or block remediation. Every decision is
append-only and replayable, so the platform can explain not just what failed, but why it believed
that failure chain and why it did or did not permit repair.
