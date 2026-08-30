# Governed Agent Runtime for OpenClaw-style Tool Calls

This slice turns the repository's evidence-first and policy-gated design into a small executable boundary for OpenClaw-style agents and other tool-calling models.

## Problem

A language model can propose a tool call, but it must not be able to:

- invent an unregistered capability;
- smuggle unsupported arguments into a known tool;
- approve its own privileged action;
- reuse an approval after the action material changes;
- override a policy block;
- loop indefinitely on the same tool call; or
- hide handler failures behind an unstructured exception.

## Runtime path

```text
agent proposal
  -> typed tool registry
  -> argument allowlist
  -> policy evaluation
  -> approval bound to proposal hash
  -> total and repeated-call budgets
  -> typed handler
  -> structured run record
```

The implementation is in `src/platform_core/governed_runtime.py`.

## Security invariants

1. Unknown tools fail closed.
2. Unknown arguments fail closed.
3. `BLOCK` cannot be overridden by an approval.
4. Privileged tools require a human approval.
5. Approval is valid only for the exact canonical proposal hash.
6. Tool-call budgets are enforced before handler execution.
7. Handler failures are converted into structured outcomes.
8. The model proposes; it never grants execution authority.

## Minimal adapter example

```python
from src.platform_core.governed_runtime import (
    Approval,
    GovernedToolRuntime,
    PolicyOutcome,
    ToolDefinition,
    ToolProposal,
)


def inspect_proxy(arguments):
    return {"target": arguments["target"], "status": "observed"}


def policy(proposal, definition):
    if definition.privileged:
        return PolicyOutcome.HUMAN_REVIEW_REQUIRED
    return PolicyOutcome.ALLOW


runtime = GovernedToolRuntime(
    tools={
        "wnrt.inspect_proxy": ToolDefinition(
            name="wnrt.inspect_proxy",
            handler=inspect_proxy,
            allowed_arguments=frozenset({"target"}),
        )
    },
    policy_evaluator=policy,
)

proposal = ToolProposal("wnrt.inspect_proxy", {"target": "wininet"})
record = runtime.run(proposal)
```

An OpenClaw skill or MCP adapter should translate its external tool-call envelope into `ToolProposal`, call this runtime, and translate `RunRecord` back to the host. The adapter must not bypass policy or invoke a privileged handler directly.

## Verification

Focused tests cover:

- safe read-only execution;
- mandatory approval for privileged tools;
- stale approval rejection;
- policy-block precedence;
- unknown-tool and argument rejection; and
- repeated-call loop protection.

Run:

```bash
pytest -q tests/test_governed_runtime.py
```

## Explicit non-claims

This slice does not claim to be a full OpenClaw implementation, an autonomous remediation system, a distributed workflow engine, or a production authorization service. It establishes one narrow, reviewable execution boundary that can later be connected to existing WNRT evidence, policy, audit, replay, and verification components.

## Next vertical slice

Connect one real read-only WNRT collector and one preview-only remediation action:

```text
wnrt.inspect_proxy
  -> normalized evidence
  -> policy outcome
  -> wnrt.preview_proxy_reset
  -> human approval
  -> execution adapter
  -> connectivity verification
  -> audit event
```

The first integration should preserve read-only defaults and keep execution disabled unless a matching human approval is supplied.
