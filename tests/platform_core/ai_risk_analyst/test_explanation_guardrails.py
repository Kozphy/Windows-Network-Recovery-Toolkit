"""Tests for AI explanation text guardrails."""

from __future__ import annotations

from src.platform_core.ai_risk_analyst.explanation_guardrails import (
    sanitize_explanation_text,
    validate_explanation_text,
)
from src.platform_core.ai_risk_analyst.models import AnalystEvidenceBundle
from src.platform_core.ai_risk_analyst.providers.local_rule_based import LocalRuleBasedAnalyst


def test_unsafe_malware_phrase_blocked() -> None:
    result = validate_explanation_text("Malware confirmed on this endpoint.")
    assert result.is_safe is False
    assert "malware confirmed" in result.violations
    assert result.recommended_rewrite


def test_unsafe_mitm_phrase_blocked() -> None:
    result = validate_explanation_text("MITM confirmed — disable proxy automatically.")
    assert result.is_safe is False


def test_safe_explanation_passes() -> None:
    text = (
        "Evidence suggests a dead localhost proxy configuration. "
        "Classification is triage only with limitations — not malware detection."
    )
    result = validate_explanation_text(text)
    assert result.is_safe is True
    assert not result.violations


def test_sanitize_rewrites_unsafe_text() -> None:
    out = sanitize_explanation_text("AI approved remediation — kill the process.")
    assert "malware" in out.lower() or "management review" in out.lower()
    assert "kill the process" not in out.lower()


def test_local_analyst_output_is_safe() -> None:
    bundle = AnalystEvidenceBundle(
        incident_id="INC-1",
        classification={"primary_classification": "DEAD_PROXY_CONFIG"},
    )
    rec = LocalRuleBasedAnalyst().analyze(bundle)
    blob = " ".join(
        [
            rec.incident_summary,
            rec.likely_hypothesis,
            rec.recommended_action,
        ]
    )
    assert validate_explanation_text(blob).is_safe
