# Portfolio Case Study 3: Reverter suspected — proxy keeps returning after disable preview

## Scenario

Operator runs remediation preview to disable WinINET proxy. Within minutes, `ProxyEnable` returns to `1` without typed confirmation in audit.

## Evidence

- `proxy_watch` timeline: disabled at 08:00, re-enabled at 08:04
- Listener may still be active; writer attribution not proven
- Policy outcome: `REQUIRE_TYPED_CONFIRMATION`, dry-run default

**Fixture:** `tests/fixtures/case_studies/case_3_reverter_suspected.json`

## Classification

**REVERTER_SUSPECTED** (secondary: `REPEATED_PROXY_REAPPEARANCE`)

## Proof tier

**T1_LOCAL_CONFIG_EVIDENCE** → **T2_RUNTIME_CORROBORATION** with watch timeline; below T4 until operator-confirmed remediation with audit.

## Risk rating

Residual **high** — repeated flip-flop increases operational and audit risk; not automatic malicious verdict.

## Recommended action

`INVESTIGATE_REVERTER` — proxy-writer attribution, extended watch, human review before apply.

## Safety boundary

- Do not kill unknown processes automatically
- Reverter suspicion ≠ compromise confirmation
- Remediation without decision logs weakens audit reconstruction

## Audit record

`human_review_required: true`, `execution_authority: human_required`, mature control **CTRL-EPR-006** with proxy-watch evidence.

## Governance report excerpt

> Human-review queue: REVERTER_SUSPECTED — accusatory-adjacent classification requires human review before remediation narrative.

## Interview talking point

“I treat reverter patterns as **control failure and attribution gap**, not malware proof. The audit chain and proxy-watch timeline are the governance artifact — not a single registry snapshot.”
