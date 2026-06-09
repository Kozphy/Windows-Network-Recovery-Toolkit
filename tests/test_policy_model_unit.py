"""Unit tests for canonical policy_model decisions."""

from __future__ import annotations

import pytest

from platform_core.policy_model import evaluate_endpoint_policy


@pytest.mark.parametrize(
    "kwargs,expected",
    [
        ({"healthy_baseline": True, "evidence_level": "OBSERVED_ONLY"}, "ALLOW_OBSERVE"),
        ({"evidence_level": "CORRELATED", "known_dev_tool": True}, "ALLOW_OBSERVE"),
        ({"evidence_level": "CORRELATED"}, "CORRELATION_ONLY_ALERT"),
        ({"evidence_level": "CORRELATED", "external_proxy": True}, "REQUIRE_TYPED_CONFIRMATION"),
        ({"evidence_level": "PROVEN_REGISTRY_WRITER", "confidence_ordinal": 0.9}, "REQUIRE_TYPED_CONFIRMATION"),
        ({"evidence_level": "OBSERVED_ONLY", "confidence_ordinal": 0.2}, "BLOCK_LOW_CONFIDENCE"),
        ({"evidence_level": "FINAL_CAUSATION", "requested_action": "kill_process"}, "BLOCK_DESTRUCTIVE"),
        ({"evidence_level": "OBSERVED_ONLY", "confidence_ordinal": 0.6}, "CORRELATION_ONLY_ALERT"),
    ],
)
def test_policy_decisions(kwargs: dict, expected: str) -> None:
    pol = evaluate_endpoint_policy(**kwargs)
    assert pol["decision"] == expected
    assert pol["execute_allowed"] is False
