"""Tests for explainable Mermaid diagram generation (read-only string transforms)."""

from __future__ import annotations

from failure_system.diagram_generator import generate_mermaid


def test_generate_mermaid_documentation_shape() -> None:
    diag = {
        "signals": {"proxy_enabled": True, "https_fail": True, "tcp_ok": True},
        "attribution": {"owner_process": "clash.exe", "classification": "vpn_client"},
        "decision": {
            "cause": "dead_local_proxy",
            "confidence": 0.91,
            "risk_level": "low",
            "recommended_fix": "Disable Proxy",
        },
    }
    out = generate_mermaid(diag)
    assert out.startswith("flowchart TD\n")
    assert "User / Network Request" in out
    assert "Process:" in out
    assert "Classification:" in out
    assert "Cause:" in out
    assert "Confidence: 0.91" in out
    assert "Fix:" in out
    assert "-->" in out


def test_generate_mermaid_empty_attribution_placeholders() -> None:
    diag = {
        "signals": {"ping": "ok"},
        "attribution": {},
        "decision": {"cause": "unknown", "confidence": 0.5, "risk_level": "medium"},
    }
    out = generate_mermaid(diag)
    assert "Not captured" in out
