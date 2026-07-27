# Decision Provenance Platform Roadmap

**Status:** Active

**Operating model:** Roadmap-driven, one focused draft pull request at a time, automated verification, manual merge.

## Delivery rules

1. Select only the first eligible unchecked implementation item.
2. Do not start a new implementation slice while its prerequisite pull request is still open or failing.
3. Keep each pull request bounded, reviewable, and independently reversible.
4. Preserve backward compatibility unless the issue explicitly approves a migration.
5. Preserve preview-only remediation and typed human confirmation.
6. Add deterministic tests for every new invariant.
7. Mark an item complete only after implementation and relevant tests pass.
8. Never merge automatically.

## Phase 1 — Decision provenance foundation

- [x] Add competing hypothesis and evidence-binding models — PR #17
- [x] Separate evidence reliability from classifier confidence — PR #17
- [x] Add backward-compatible `RiskDecisionRecordV3` — PR #17
- [x] Bind approval records to deterministic decision material — PR #17
- [ ] Review, validate, and merge PR #17

## Phase 2 — Deterministic reasoning

- [ ] Add deterministic hypothesis evaluator
- [ ] Add reason-code registry
- [ ] Add missing-evidence recommendations
- [ ] Add contradiction-resolution rules
- [ ] Add counterfactual decision-reversal conditions

## Phase 3 — Governance

- [ ] Add append-only approval ledger
- [ ] Add separation-of-duties policy
- [ ] Add approval expiration and invalidation
- [ ] Add reviewer queue service and API
- [ ] Add decision supersession links

## Phase 4 — Execution accountability

- [ ] Add execution receipts
- [ ] Add before/after state hashes
- [ ] Add rollback references
- [ ] Add outcome verification
- [ ] Distinguish execution success from problem resolution

## Phase 5 — Replay and drift

- [ ] Add decision replay diff
- [ ] Detect evidence drift
- [ ] Detect classifier drift
- [ ] Detect policy drift
- [ ] Detect control-set drift
- [ ] Detect nondeterministic replay results

## Phase 6 — Platform surfaces

- [ ] Add `/v1/decisions/propose`
- [ ] Add `/v1/decisions/review`
- [ ] Add `/v1/decisions/approve`
- [ ] Add `/v1/decisions/preview`
- [ ] Add `/v1/decisions/execute`
- [ ] Add `/v1/decisions/verify`
- [ ] Add `/v1/decisions/replay`
- [ ] Add `/v1/decisions/diff`

## Completion evidence for each slice

Each implementation pull request should include:

- a narrow problem statement;
- explicit non-goals;
- deterministic tests;
- compatibility and safety impact;
- commands executed and results;
- known limitations;
- the next eligible roadmap item.
