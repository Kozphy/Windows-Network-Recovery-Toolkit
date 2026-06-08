from __future__ import annotations

from backend.observability_metrics import (
    confidence_label,
    hostname_label,
    record_policy_decision,
    record_reasoning_pipeline,
    sanitize_label,
)
from backend.prometheus_exporter import render_prometheus_text, reset_metrics_for_tests


def test_hostname_label_is_hashed_not_raw() -> None:
    label = hostname_label("my-workstation.corp.local")
    assert label != "my-workstation.corp.local"
    assert len(label) == 16


def test_confidence_label_buckets() -> None:
    assert confidence_label(0.1) == "low"
    assert confidence_label(0.5) == "medium"
    assert confidence_label(0.7) == "high"
    assert confidence_label(0.95) == "very_high"


def test_labeled_metrics_render_prometheus_format() -> None:
    reset_metrics_for_tests()
    record_policy_decision(
        endpoint_id="ep-test",
        policy_outcome="BLOCK",
        hypothesis="loopback_proxy",
        confidence=0.8,
    )
    body = render_prometheus_text()
    assert "policy_block_total{" in body
    assert 'hostname="' in body
    assert 'policy="block"' in body
    assert 'hypothesis="loopback_proxy"' in body
    assert 'confidence="high"' in body


def test_record_reasoning_pipeline_increments_core_counters() -> None:
    reset_metrics_for_tests()
    record_reasoning_pipeline(
        endpoint_id="local",
        correlation={
            "accepted_hypothesis": "dns_failure",
            "confidence_score": 0.4,
            "policy_decision": {"outcome": "PREVIEW"},
            "proof_result": {"status": "NOT_RUN"},
            "hypothesis_ranking": [],
            "observations": [{"signal_name": "proxy_enable", "value": 1}],
            "events": [],
        },
    )
    body = render_prometheus_text()
    assert "hypothesis_generated_total" in body
    assert "policy_preview_total" in body
    assert "proxy_change_total" in body


def test_sanitize_label() -> None:
    assert sanitize_label("Loopback Proxy!") == "loopback_proxy_"
