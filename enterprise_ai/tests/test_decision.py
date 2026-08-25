from enterprise_ai.decision import DecisionEngine


def test_human_review_gate_blocks_unapproved_action():
    decision = DecisionEngine().decide(
        proposed_action="propose_remediation",
        confidence=0.95,
        min_confidence=0.90,
        allowed_actions=["propose_remediation"],
        require_human_review=True,
        human_approved=False,
    )
    assert decision.approved is False
    assert decision.reason == "human_review_required"


def test_low_confidence_is_blocked():
    decision = DecisionEngine().decide(
        proposed_action="diagnose",
        confidence=0.60,
        min_confidence=0.85,
        allowed_actions=["diagnose"],
        require_human_review=False,
    )
    assert decision.approved is False
    assert decision.reason == "confidence_below_threshold"


def test_approved_action_passes_when_all_gates_satisfied():
    decision = DecisionEngine().decide(
        proposed_action="diagnose",
        confidence=0.99,
        min_confidence=0.85,
        allowed_actions=["diagnose"],
        require_human_review=False,
    )
    assert decision.approved is True
