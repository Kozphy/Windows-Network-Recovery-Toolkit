# RiskClaw Runtime Foundation

RiskClaw is the product-agent control layer for the Technology Risk & Control
Analytics Platform. It coordinates strict contracts, skill allowlists, typed
tool definitions, and policy decisions while reusing the repository's existing
deterministic evidence and governance core.

This foundation does **not** add an LLM loop, Gateway, autonomous remediation,
or a generic shell tool.

## Relationship to existing agent code

| Path | Responsibility |
| ------ | ---------------- |
| `src/platform_core/agents/` | Deterministic pipeline stage output contracts |
| `src/platform_core/openclaw/` | Policy-gated coding automation and draft PR workflow |
| `windows_network_toolkit/agent/` | Existing read-only endpoint collection cycle |
| `riskclaw/` | Product-agent runtime contracts and capability governance |

RiskClaw does not replace those modules. It provides the boundary needed to
compose them later without allowing a model to call arbitrary Python or Windows
functions.

## Phase 1 flow

```text
proposed skill
  -> strict SKILL.md loader
  -> skill tool allowlist
  -> typed ToolRegistry lookup
  -> ToolPolicyEngine
  -> ALLOW / PREVIEW / REQUIRE_APPROVAL / BLOCK
```

The `ToolPolicyEngine` accepts an optional outcome from the canonical policy
engine in `src/platform_core/policy/engine.py`. It may preserve or tighten that
outcome; it cannot weaken it. Unknown outcomes and rollback requirements fail
closed.

## Contracts

`riskclaw/schemas.py` defines:

- `AgentDefinition`
- `SkillDefinition`
- `ToolDefinition`
- `InvestigationSession`
- `ApprovalRecord`
- `RiskClawAuditEvent`
- `ToolPolicyResult`

Models reject unknown fields. Sessions are incident-scoped rather than generic
chat histories. Approval records require decision attribution and timestamps.

## Tool registry

The registry stores an explicit `ToolDefinition`, Pydantic input model, and
handler. It rejects duplicate and unknown names and validates payloads before a
future execution layer receives them.

The registry intentionally has no public `execute` method in Phase 1. Adding a
handler to the registry does not authorize it. Execution must be introduced
through a policy-gated runtime with audit emission.

## Skill format

RiskClaw skills use a `SKILL.md` with strict YAML frontmatter:

```markdown
---
name: proxy-risk-investigation
description: Diagnose Windows proxy drift using deterministic evidence.
allowed_tools:
  - proxy.collect
  - proxy.classify
risk_level: read_only
requires_human_approval: false
---

# Proxy Risk Investigation

1. Collect WinINET and WinHTTP evidence.
2. Inspect referenced localhost listeners.
3. Run the deterministic classifier.
4. Preserve proof tier and limitations.

Never modify the registry or claim malware attribution.
```

When the loader receives a known-tool set, any unregistered tool reference is
rejected.

## Safety invariants

- No arbitrary shell, PowerShell, registry, firewall, process, or adapter tool
- No LLM-authorized execution
- Tool not listed by the selected skill means `BLOCK`
- Tool risk above the skill boundary means `BLOCK`
- Unknown canonical policy outcome means `BLOCK`
- `ROLLBACK_REQUIRED` means `BLOCK` until a rollback-plan contract exists
- Policy permission is not a safety guarantee
- Recommendation is not execution authority

## Validation

```powershell
pytest -q tests/riskclaw
ruff check riskclaw tests/riskclaw
mypy riskclaw
```

## Next bounded increment

Wrap four existing deterministic read-only capabilities:

1. proxy evidence collection
2. proxy state classification
3. control testing
4. governance summary generation

That increment should add a policy-gated executor and canonical audit events.
It must not add live remediation.
