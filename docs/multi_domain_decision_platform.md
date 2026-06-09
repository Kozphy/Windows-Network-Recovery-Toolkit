# Multi-Domain Decision Platform

## From Windows Toolkit to Multi-Domain Decision Platform

Windows proxy drift, security alerts, cloud incidents, infrastructure failures, and market events are all **event-state decision problems**. The platform normalizes events, builds evidence trees, ranks hypotheses, scores decisions, applies policy guardrails, tracks outcomes, and supports deterministic replay.

**This is not** an autonomous repair tool, trading bot, or EDR replacement. All decisions are **research / preview / recommendation only**.

## Pipeline

```text
Any Domain Event
  → Normalized Event
  → Evidence Tree
  → Candidate Hypotheses
  → Candidate Decisions
  → Decision Scoring
  → Policy Validation
  → Outcome Tracking
  → Audit Log
  → Replay
  → Learning Metrics
```

## Domains (fixture-based v1)

| Domain | Examples |
|--------|----------|
| Windows | Proxy localhost, DNS failure, browser path |
| Security | Encoded PowerShell, registry write, listener |
| Cloud | Error rate, IAM change, failed deployment |
| Infrastructure | CPU spike, disk pressure, restart loop |
| Market | CPI, token unlock, ETF flow, protocol upgrade |

Fixtures: `tests/fixtures/domains/<domain>/*.json`

## CLI

```bash
python -m src platform events
python -m src platform events --domain windows
python -m src platform evidence --event-id win-proxy-localhost-001
python -m src platform decide --event-id win-proxy-localhost-001
python -m src platform outcome --decision-id dec-inspect-proxy
python -m src platform replay
python -m src platform metrics
```

Audit JSONL: `logs/multi_domain_audit.jsonl` (append-only, replayable except live timestamp).

## Epistemic rules (Big 4 / risk framing)

- Observation is not proof.
- Correlation is not causation.
- Confidence is not certainty.
- Recommendation is not execution permission.
- Every decision must be auditable.

## Engineering framing (FAANG)

- Domain adapters (`src/domains/`)
- Normalized event model (`src/core/event.py`)
- Deterministic replay (`src/core/replay.py`)
- Policy guardrails (`src/core/policy_engine.py`)
- Outcome metrics (`src/core/outcome_engine.py`)
- Observability-ready JSON outputs

## Code layout

```text
src/core/           # Models + engines (domain-agnostic)
src/domains/        # Windows, security, cloud, infrastructure, market adapters
src/platform_handlers.py
tests/fixtures/domains/
tests/test_multi_domain_platform.py
```

Existing Windows commands (`diagnose`, `proxy-policy`, etc.) are unchanged.
