from __future__ import annotations

from pathlib import Path

import pytest

from agent.classifier import classify_with_primary
from agent.collector import load_evidence_from_json

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def test_classifier_healthy_top_is_unknown() -> None:
    ev = load_evidence_from_json(FIXTURES / "healthy_network.json")
    primary, _ranked = classify_with_primary(ev)
    assert primary is not None
    assert primary.category == "unknown"


def test_classifier_dns_primary() -> None:
    ev = load_evidence_from_json(FIXTURES / "dns_failure.json")
    primary, _ranked = classify_with_primary(ev)
    assert primary.category == "dns_issue"
    assert primary.confidence >= 0.8


def test_classifier_proxy_primary() -> None:
    ev = load_evidence_from_json(FIXTURES / "proxy_failure.json")
    primary, _ranked = classify_with_primary(ev)
    assert primary.category == "proxy_issue"


def test_classifier_https_layer() -> None:
    ev = load_evidence_from_json(FIXTURES / "https_failure.json")
    primary, ranked = classify_with_primary(ev)
    categories = [r.category for r in ranked]
    assert primary.category == "https_issue"
    assert "https_issue" in categories


def test_classifier_connection_exhaustion() -> None:
    ev = load_evidence_from_json(FIXTURES / "connection_exhaustion.json")
    primary, _ranked = classify_with_primary(ev)
    assert primary.category == "connection_exhaustion"
