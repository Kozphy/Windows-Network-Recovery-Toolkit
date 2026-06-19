# ADR-0006: AI-Assisted, Not AI-Authorized

## Status

Accepted

## Context

AI tooling can accelerate investigation narratives, report formatting, and hypothesis suggestions. Without explicit boundaries, reviewers assume models authorize remediation or upgrade proof tiers — creating compliance and safety liability.

## Decision

AI usage is **assistive only**, documented in `AI_TRANSPARENCY_SECTION` of `audit_report.py`:

**AI may assist with:**

- Summarizing evidence timelines
- Formatting governance markdown
- Suggesting next checks (Sysmon, health re-run)

**AI does not authorize:**

- Registry mutation or process kill
- Policy gate bypass
- Proof tier upgrade
- Malware or MITM verdict language
- Skipping human review for accusatory-adjacent classifications

All execution paths remain policy-gated with typed confirmation. `unsafe_inferences_blocked` includes: "AI output does not authorize execution."

## Alternatives considered

| Alternative | Why rejected |
|-------------|--------------|
| LLM as classification primary | Non-deterministic; breaks CI golden fixtures |
| Hidden AI in CLI output | Fails audit transparency |
| No AI documentation | Interviewers assume autonomous agent |

## Consequences

- Human-review queue remains mandatory for `REVERTER_SUSPECTED`, `UNKNOWN_LOCAL_PROXY`, etc.
- Portfolio demos should disclose if narrative was AI-edited
- Future RAG features must attach same governance envelope

## Security considerations

- Prompt injection via third-party page titles must not flow into execution commands
- AI suggestions treated as untrusted input — same as operator notes (T0)

## Audit considerations

- Governance report includes AI transparency section for committee packets
- Not a substitute for model risk management framework at enterprise scale

## What this prevents

- "The AI said disable proxy" as audit justification
- Autonomous agent loops mutating registry

## What this does not prove

- That no AI was used in doc authoring (portfolio honesty is process-level)
- Enterprise MRM compliance for production LLM deployment

## Interview defense

"AI helps me write the report faster — it doesn't sign the change. Execution authority stays human_required with hash-chained audit."
