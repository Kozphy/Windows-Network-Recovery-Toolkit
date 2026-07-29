from src.platform_core.control_testing import (
    ControlDefinition,
    EvidenceRequirement,
    TestConclusion,
    evaluate_control,
)


def _control() -> ControlDefinition:
    return ControlDefinition(
        control_id="CTRL-001",
        version="1.0",
        name="Dead WinINET Proxy Detection",
        objective="Detect configured localhost proxy paths without a corroborating listener.",
        requirements=(
            EvidenceRequirement(
                evidence_type="proxy_state",
                required_fields=("wininet_proxy_enabled", "wininet_proxy_server"),
                minimum_tier=1,
                description="WinINET proxy state captured",
            ),
            EvidenceRequirement(
                evidence_type="listener_state",
                required_fields=("listener_found", "localhost_port"),
                minimum_tier=2,
                description="Local listener state corroborated",
            ),
        ),
    )


def test_control_pass_requires_all_explicit_evidence():
    evidence = [
        {
            "event_id": "proxy-1",
            "evidence_type": "proxy_state",
            "evidence_tier": "T1_STATE_EVIDENCE",
            "normalized_fields": {
                "wininet_proxy_enabled": True,
                "wininet_proxy_server": "127.0.0.1:7890",
            },
        },
        {
            "event_id": "listener-1",
            "evidence_type": "listener_state",
            "evidence_tier": "T2_RUNTIME_EVIDENCE",
            "normalized_fields": {"listener_found": False, "localhost_port": 7890},
        },
    ]

    result = evaluate_control(
        _control(), evidence, incident_id="inc-1", tested_at_utc="2026-07-30T00:00:00Z"
    )

    assert result.conclusion is TestConclusion.PASS
    assert result.evidence_refs == ("listener-1", "proxy-1")
    assert not result.missing_requirements


def test_control_partial_does_not_invent_listener_evidence():
    evidence = [
        {
            "event_id": "proxy-1",
            "evidence_type": "proxy_state",
            "evidence_tier": "T1_STATE_EVIDENCE",
            "normalized_fields": {
                "wininet_proxy_enabled": True,
                "wininet_proxy_server": "127.0.0.1:7890",
            },
        }
    ]

    result = evaluate_control(
        _control(), evidence, incident_id="inc-1", tested_at_utc="2026-07-30T00:00:00Z"
    )

    assert result.conclusion is TestConclusion.PARTIAL
    assert result.missing_requirements == ("Local listener state corroborated",)


def test_control_not_tested_when_no_evidence_exists():
    result = evaluate_control(
        _control(), [], incident_id="inc-1", tested_at_utc="2026-07-30T00:00:00Z"
    )

    assert result.conclusion is TestConclusion.NOT_TESTED
    assert "not tested" in result.rationale.lower()


def test_test_id_is_deterministic_for_retry_safe_ingestion():
    evidence = [
        {
            "event_id": "proxy-1",
            "evidence_type": "proxy_state",
            "evidence_tier": 1,
            "normalized_fields": {
                "wininet_proxy_enabled": True,
                "wininet_proxy_server": "127.0.0.1:7890",
            },
        }
    ]

    first = evaluate_control(
        _control(), evidence, incident_id="inc-1", tested_at_utc="2026-07-30T00:00:00Z"
    )
    second = evaluate_control(
        _control(), evidence, incident_id="inc-1", tested_at_utc="2026-07-30T00:01:00Z"
    )

    assert first.test_id == second.test_id


def test_pass_never_grants_execution_authority():
    result = evaluate_control(
        _control(),
        [
            {
                "event_id": "proxy-1",
                "evidence_type": "proxy_state",
                "evidence_tier": 1,
                "normalized_fields": {
                    "wininet_proxy_enabled": True,
                    "wininet_proxy_server": "127.0.0.1:7890",
                },
            },
            {
                "event_id": "listener-1",
                "evidence_type": "listener_state",
                "evidence_tier": 2,
                "normalized_fields": {"listener_found": False, "localhost_port": 7890},
            },
        ],
        incident_id="inc-1",
        tested_at_utc="2026-07-30T00:00:00Z",
    )

    assert "execution_authority" not in result.to_dict()
    assert any("does not authorize remediation" in item for item in result.limitations)
