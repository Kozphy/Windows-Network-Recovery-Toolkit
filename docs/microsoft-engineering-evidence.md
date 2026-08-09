# Microsoft Engineering Evidence Review

This document turns the portfolio from a feature inventory into an engineering-evidence package. It is intentionally scoped as a production-shaped prototype, not a claim that the system has operated a Microsoft-scale fleet.

## Golden scenario

The canonical review scenario is a Windows endpoint that remains network-connected while application traffic fails because of proxy configuration drift or a dead localhost proxy.

```text
Requirement
  -> deterministic evidence collection
  -> classification with explicit limitations
  -> control tests
  -> policy gate
  -> human approval boundary
  -> deterministic remediation preview/apply boundary
  -> verification
  -> append-only audit evidence
  -> governance metrics
```

## Engineering questions the repository must answer

### Reliability
- What failure is detected?
- What evidence distinguishes configuration drift from an unsupported security conclusion?
- What is the false-positive surface?
- What happens when evidence is incomplete?
- How is recovery verified rather than assumed?

### Safety
- Which operations are read-only?
- Which operations mutate endpoint state?
- What requires explicit operator approval?
- Can an AI-generated explanation authorize execution? **No.**
- How is rollback represented and audited?

### Scale
The portfolio should demonstrate scale through reproducible simulation rather than unsupported production claims. Record endpoint count, seed, scenario mix, runtime, success/failure counts, and latency distribution for every benchmark run.

### Observability
A reviewer should be able to reconstruct:
1. what evidence was collected;
2. what decision was made;
3. why the policy allowed or denied an action;
4. who/what authorized the transition;
5. whether verification succeeded;
6. whether the audit chain remains valid.

## Evidence scorecard

| Dimension | Required evidence | Acceptance criterion |
|---|---|---|
| Correctness | deterministic replay + tests | same fixture and seed produce the same decision |
| Safety | policy/safety contract tests | mutation paths fail closed without required approval |
| Reliability | fault scenarios | expected classification and verification result are asserted |
| Performance | benchmark artifact | machine-readable results include P50/P95 and throughput |
| Security | threat model | trust boundaries and abuse cases have mitigations/tests |
| Auditability | hash-chain verification | tampering is detectable |
| Operability | runbook | reviewer can reproduce the golden scenario |
| Design judgment | ADRs | important trade-offs record alternatives and consequences |

## Metrics contract

Do not publish invented performance numbers. Generate them from reproducible runs and preserve raw evidence.

Recommended fields:

```json
{
  "scenario": "mixed_proxy_failures",
  "endpoints": 1000,
  "seed": 42,
  "duration_seconds": 0.0,
  "throughput_endpoints_per_second": 0.0,
  "latency_ms": {"p50": 0.0, "p95": 0.0, "p99": 0.0},
  "classification_counts": {},
  "verification_success_rate": 0.0,
  "generated_at": "RFC3339 timestamp",
  "commit_sha": "git sha"
}
```

## Fault-injection matrix

| Scenario | Injected condition | Expected behavior |
|---|---|---|
| dead localhost proxy | configured proxy has no listener | classify reliability condition; do not claim malware |
| WinINET/WinHTTP drift | conflicting proxy paths | surface drift evidence and limitations |
| TLS path mismatch | paths produce different TLS observations | report mismatch; avoid unsupported attribution |
| missing evidence | collector unavailable/partial | degrade to insufficient proof; fail closed for mutation |
| audit tamper | modify prior JSONL record | chain verification fails |
| denied remediation | policy/approval absent | preview/deny; no endpoint mutation |

Each scenario should eventually have a deterministic fixture and an automated assertion.

## ADR backlog

High-value design decisions to keep explicit:

1. Deterministic execution instead of LLM-authorized remediation.
2. Dry-run/preview as the default mutation posture.
3. Evidence tiers and `limitations[]` instead of probabilistic security verdicts.
4. Append-only hash-chained JSONL for portable portfolio audit evidence.
5. Fixture/replay simulation instead of claiming unobserved production scale.
6. Separation between endpoint evidence, decision policy, execution, and reporting.

## Interview defense

A strong explanation of this repository should be able to answer:

> Why did you design it this way? What breaks? How do you know it works? What happens at 10,000 endpoints?

The expected answer is evidence-based: point to a deterministic test, benchmark, fault scenario, threat-model mitigation, ADR, or explicit known limitation. Never substitute an unsupported scale or production claim.

## Definition of done for the next engineering milestone

- [ ] Golden scenario runs from one documented command/path.
- [ ] At least six deterministic fault scenarios are executable in CI.
- [ ] Benchmark output is machine-readable and reproducible by seed.
- [ ] P50/P95/P99 and throughput are calculated from actual runs.
- [ ] Security-sensitive transitions have negative tests.
- [ ] Audit tampering causes a deterministic verification failure.
- [ ] At least five consequential design decisions have ADRs.
- [ ] README links directly to generated evidence rather than only describing features.
- [ ] No README/resume statement implies unmeasured production scale.
