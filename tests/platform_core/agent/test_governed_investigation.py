from __future__ import annotations

import pytest

from src.platform_core.agent.orchestrator import Decision, GovernedInvestigation, InvestigationResult


def _collect(incident):
    return {"endpoint": incident["endpoint"], "proxy_listener": False}


def _classify(evidence):
    return {
        "incident_class": "DEAD_PROXY_CONFIG",
        "proof_tier": "T3",
        "limitations": ["process attribution not collected"],
    }


def _explain(evidence, classification):
    return f"{classification['incident_class']} on {evidence['endpoint']}"


def _preview(classification):
    return {
        "action": "clear_user_proxy",
        "mode": "preview",
        "requires_typed_confirmation": True,
    }


def test_explanation_only_is_default():
    result = GovernedInvestigation(
        collect_evidence=_collect,
        classify=_classify,
        explain=_explain,
        preview_remediation=_preview,
    ).run({"endpoint": "host-001"})

    assert result.decision is Decision.EXPLAIN_ONLY
    assert result.execution_authorized is False
    assert result.remediation_preview is None


def test_preview_requires_human_review():
    result = GovernedInvestigation(
        collect_evidence=_collect,
        classify=_classify,
        explain=_explain,
        preview_remediation=_preview,
    ).run({"endpoint": "host-001"}, request_remediation_preview=True)

    assert result.decision is Decision.HUMAN_REVIEW_REQUIRED
    assert result.remediation_preview["mode"] == "preview"
    assert result.execution_authorized is False


def test_agent_result_cannot_authorize_execution():
    with pytest.raises(ValueError, match="cannot authorize execution"):
        InvestigationResult(
            decision=Decision.EXPLAIN_ONLY,
            evidence={},
            classification={},
            explanation="invalid",
            execution_authorized=True,
        )


def test_blocked_classification_suppresses_preview():
    workflow = GovernedInvestigation(
        collect_evidence=_collect,
        classify=lambda evidence: {"blocked": True, "limitations": []},
        explain=_explain,
        preview_remediation=_preview,
    )

    result = workflow.run({"endpoint": "host-001"}, request_remediation_preview=True)

    assert result.decision is Decision.BLOCKED
    assert result.remediation_preview is None
