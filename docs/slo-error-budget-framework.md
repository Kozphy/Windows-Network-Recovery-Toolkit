# SLI / SLO / Error-Budget Framework

## Purpose

This framework defines how a future production deployment should reason about reliability. The values below are **candidate objectives for engineering experiments**, not claims about current production performance.

## Reliability principles

1. Availability alone is insufficient: an endpoint may be online while decision evidence is stale or incomplete.
2. Safety beats speed for mutation-capable workflows.
3. SLOs apply to explicitly defined user journeys and evidence paths.
4. Error budgets are decision tools, not badges.
5. Measurements must distinguish synthetic/replay environments from production telemetry.

## Primary SLIs

| SLI | Definition | Why it matters |
|---|---|---|
| Evidence ingest success | accepted valid envelopes / valid envelopes sent | source visibility |
| Decision success | completed deterministic decisions / valid decision requests | core service usefulness |
| End-to-end decision latency | evidence observed -> decision persisted | operator responsiveness |
| Evidence freshness | now - newest usable evidence per source | prevents stale confidence |
| Audit durability | durable audit writes / required audit writes | governance integrity |
| Replay determinism | identical deterministic outputs / repeated identical inputs | reproducibility |
| Policy-gate correctness | expected allow/block/preview decisions / labeled cases | safety |
| Verification completion | required post-action verifications completed / required | closes action loop |

## Candidate SLOs

These are starting hypotheses for load tests and design review.

| Journey | Candidate objective | Window |
|---|---:|---:|
| Valid evidence ingest | >= 99.9% | 28 days |
| Read-only decision completion | >= 99.9% | 28 days |
| Decision latency | 99% <= 5 s | 28 days |
| High-risk policy evaluation | 99% <= 2 s | 28 days |
| Required audit persistence | >= 99.99% | 28 days |
| Deterministic fixture replay | 100% agreement | CI / release gate |

Do not copy these percentages into portfolio claims unless a measured environment and observation window are attached.

## Error-budget math

For a success-rate SLO:

```text
error_budget = 1 - SLO
allowed_bad_events = total_eligible_events * error_budget
```

Example only: a 99.9% objective permits 0.1% bad eligible events in the chosen window.

For latency SLOs, the budget is the fraction of eligible events exceeding the latency threshold.

## Burn rate

```text
burn_rate = observed_bad_event_ratio / error_budget_ratio
```

Interpretation:

- `< 1x`: consuming budget slower than the window permits;
- `1x`: exactly on budget trajectory;
- `> 1x`: budget is being consumed too quickly;
- large multi-window burn: page-worthy reliability risk.

## Multi-window alert policy

A production implementation should prefer paired windows over a single threshold, for example:

- fast burn: short window + severe threshold;
- slow burn: long window + lower threshold.

This reduces alerting on tiny transient noise while still catching sustained degradation.

## Error-budget policy

When a service has exhausted or is projected to exhaust its error budget:

1. stop expanding risky mutation capability;
2. prioritize reliability regressions over feature throughput;
3. reduce optional work such as non-critical analytics;
4. investigate top error classes and queue-age growth;
5. require explicit review before relaxing an SLO.

The policy should never encourage hiding failures by changing denominators or excluding inconvenient events after the fact.

## Degradation hierarchy

During overload, degrade in this order:

1. optional dashboard refresh;
2. non-critical aggregate analytics;
3. low-priority replay/backfill;
4. read-only enrichment;

Preserve as long as possible:

- evidence ingestion;
- policy safety gates;
- required audit persistence;
- explicit human approval state.

## SLO metadata contract

Every published SLO result should carry:

- service / journey name;
- SLI formula;
- inclusion and exclusion rules;
- threshold and target;
- observation window;
- environment (`fixture`, `synthetic`, `staging`, `production`);
- sample size;
- measurement source;
- code/config revision;
- known instrumentation gaps.

## Research integration

The research layer should not equate benchmark speed with an SLO. The experiment runner records local p50/p95/p99 and throughput as **benchmark observations**. A production SLO requires sustained service telemetry under realistic failure modes.

## Required chaos experiments before stronger claims

- worker termination during active processing;
- broker unavailable / delayed;
- duplicate delivery storm;
- malformed schema burst;
- downstream audit-store latency;
- classifier timeout;
- policy-store unavailability;
- partition hotspot;
- replay after partial failure.

For each experiment record impact, recovery path, data loss, duplicate effects, and whether safety boundaries remained intact.
