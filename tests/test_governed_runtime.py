from src.platform_core.governed_runtime import (
    Approval,
    ExecutionBudget,
    GovernedToolRuntime,
    PolicyOutcome,
    RunStatus,
    ToolDefinition,
    ToolProposal,
)


def _read_handler(arguments):
    return {"observed": arguments["target"]}


def _write_handler(arguments):
    return {"changed": arguments["target"]}


def _policy(proposal, definition):
    if proposal.tool_name == "dangerous.delete_all":
        return PolicyOutcome.BLOCK
    if definition.privileged:
        return PolicyOutcome.HUMAN_REVIEW_REQUIRED
    return PolicyOutcome.ALLOW


def _runtime(*, budget=None):
    return GovernedToolRuntime(
        {
            "network.inspect": ToolDefinition(
                name="network.inspect",
                handler=_read_handler,
                allowed_arguments=frozenset({"target"}),
            ),
            "network.reset_proxy": ToolDefinition(
                name="network.reset_proxy",
                handler=_write_handler,
                allowed_arguments=frozenset({"target"}),
                privileged=True,
            ),
            "dangerous.delete_all": ToolDefinition(
                name="dangerous.delete_all",
                handler=_write_handler,
                allowed_arguments=frozenset({"target"}),
                privileged=True,
            ),
        },
        _policy,
        budget=budget,
    )


def test_read_only_tool_executes_without_self_granted_authority():
    proposal = ToolProposal("network.inspect", {"target": "proxy"})

    record = _runtime().run(proposal)

    assert record.status is RunStatus.EXECUTED
    assert record.result == {"observed": "proxy"}


def test_privileged_tool_requires_human_approval():
    proposal = ToolProposal("network.reset_proxy", {"target": "wininet"})

    record = _runtime().run(proposal)

    assert record.status is RunStatus.REVIEW_REQUIRED
    assert record.policy_outcome is PolicyOutcome.HUMAN_REVIEW_REQUIRED


def test_approval_is_bound_to_exact_proposal_hash():
    original = ToolProposal("network.reset_proxy", {"target": "wininet"})
    changed = ToolProposal("network.reset_proxy", {"target": "winhttp"})
    approval = Approval("approval-1", original.proposal_hash, "operator@example.test")

    record = _runtime().run(changed, approval=approval)

    assert record.status is RunStatus.BLOCKED
    assert "stale" in record.reason


def test_matching_approval_allows_privileged_execution():
    proposal = ToolProposal("network.reset_proxy", {"target": "wininet"})
    approval = Approval("approval-1", proposal.proposal_hash, "operator@example.test")

    record = _runtime().run(proposal, approval=approval)

    assert record.status is RunStatus.EXECUTED
    assert record.result == {"changed": "wininet"}


def test_unknown_tool_and_unknown_arguments_fail_closed():
    unknown_tool = _runtime().run(ToolProposal("missing.tool", {}))
    unknown_argument = _runtime().run(
        ToolProposal("network.inspect", {"target": "proxy", "shell": "whoami"})
    )

    assert unknown_tool.status is RunStatus.INVALID
    assert unknown_argument.status is RunStatus.INVALID
    assert unknown_tool.policy_outcome is PolicyOutcome.BLOCK
    assert unknown_argument.policy_outcome is PolicyOutcome.BLOCK


def test_policy_block_cannot_be_overridden_by_approval():
    proposal = ToolProposal("dangerous.delete_all", {"target": "everything"})
    approval = Approval("approval-1", proposal.proposal_hash, "operator@example.test")

    record = _runtime().run(proposal, approval=approval)

    assert record.status is RunStatus.BLOCKED
    assert record.result is None


def test_repeated_call_budget_stops_agent_loops():
    budget = ExecutionBudget(max_total_calls=5, max_repeated_calls=1)
    runtime = _runtime(budget=budget)
    proposal = ToolProposal("network.inspect", {"target": "proxy"})

    first = runtime.run(proposal)
    second = runtime.run(proposal)

    assert first.status is RunStatus.EXECUTED
    assert second.status is RunStatus.BUDGET_EXHAUSTED
