"""Tests for plain-English ``explanation_text`` generation."""

from __future__ import annotations

from failure_system.explanation_text import generate_explanation_text


def test_explanation_text_shape() -> None:
    diag = {
        "signals": {
            "ping_ip": "OK",
            "dns_lookup": "Fail",
            "https_fetch": "Fail",
            "winhttp_direct": "Yes",
            "proxy_line": "No",
            "intermittent": "No",
        },
        "attribution": {"owner_process": "example.exe", "classification": "vpn_client"},
        "decision": {
            "cause": "DNS resolution failure",
            "confidence": 0.88,
            "risk_level": "low",
            "recommended_fix": "Review resolver settings and toolkit DNS guidance.",
        },
    }
    out = generate_explanation_text(diag)
    assert "DNS" in out or "dns" in out.lower()
    assert "0.88" in out
    assert "example.exe" in out or "example" in out
    sentences = [s for s in out.replace("?", ".").split(".") if s.strip()]
    assert len(sentences) >= 2


def test_explanation_text_no_attribution() -> None:
    diag = {
        "signals": {"ping_ip": "Fail"},
        "attribution": {},
        "decision": {"cause": "unknown", "confidence": 0.3, "risk_level": "low"},
    }
    out = generate_explanation_text(diag)
    assert "not captured" in out.lower() or "Observed signals" in out
