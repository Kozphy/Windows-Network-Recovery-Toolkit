"""Step 3 — proxy policy engine tests."""

from __future__ import annotations

from pathlib import Path

from src.policy.models import PolicyDecisionKind, PolicySeverity
from src.policy.proxy_policy_engine import evaluate_proxy_policy_input
from src.proxy_guard.incident_pipeline import analyze_fixture
from src.replay.fixture_loader import load_fixture

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "proxy_incidents"


def test_cursor_observe_low_severity() -> None:
    bundle = analyze_fixture(load_fixture(FIXTURES / "cursor_known_proxy.json"))
    pol = bundle["policy"]
    assert pol["decision"] in ("OBSERVE", "ALLOW")
    assert pol["severity"] in ("LOW", "MEDIUM")


def test_suspicious_block_recommended() -> None:
    bundle = analyze_fixture(load_fixture(FIXTURES / "suspicious_powershell_temp_proxy.json"))
    assert bundle["policy"]["decision"] == PolicyDecisionKind.BLOCK_RECOMMENDED.value
    assert bundle["policy"]["severity"] == PolicySeverity.CRITICAL.value
    assert bundle["policy"]["requires_confirmation"] is True


def test_mitm_escalate_review() -> None:
    bundle = analyze_fixture(load_fixture(FIXTURES / "external_proxy_mitm_risk.json"))
    assert bundle["policy"]["decision"] == PolicyDecisionKind.ESCALATE_REVIEW.value


def test_correlation_only_alert() -> None:
    bundle = analyze_fixture(load_fixture(FIXTURES / "correlation_only_listener.json"))
    assert bundle["policy"]["decision"] == PolicyDecisionKind.CORRELATION_ONLY_ALERT.value
    assert "registry writer proof unavailable" in " ".join(bundle["policy"]["explanation"]).lower()


def test_unknown_local_alert() -> None:
    bundle = analyze_fixture(load_fixture(FIXTURES / "unknown_node_powershell_proxy.json"))
    assert bundle["policy"]["decision"] == PolicyDecisionKind.ALERT.value
    assert "kill_process" in bundle["policy"]["blocked_actions"]


def test_autoconfigurl_alert() -> None:
    from src.classification.models import ProcessClassificationKind, ProcessClassificationResult
    from src.policy.models import ProxyPolicyInput, ProxyPolicyUserConfig

    inp = ProxyPolicyInput(
        causation_level="FINAL_CAUSATION",
        classification_result=ProcessClassificationResult(
            classification=ProcessClassificationKind.KNOWN_DEV_PROXY,
            confidence=0.8,
            summary="dev",
        ),
        proxy_before={},
        proxy_after={"auto_config_url": "http://evil/pac.js"},
        changed_fields=["AutoConfigURL"],
        user_config=ProxyPolicyUserConfig(),
    )
    pol = evaluate_proxy_policy_input(inp)
    assert pol.decision == PolicyDecisionKind.ALERT
    assert pol.severity == PolicySeverity.HIGH
