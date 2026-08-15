"""Fixture-only tests for the unified operator incident card."""

from __future__ import annotations

from pathlib import Path

from src.cli import main
from src.proxy_drift.operator_incident_card import (
    compose_operator_incident_card,
    load_operator_incident_fixture,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "operator_incident"


def test_rewriter_outranks_dead_proxy() -> None:
    card = load_operator_incident_fixture(FIXTURES / "rewriter.json")
    assert card["primary_class"] == "LOCALHOST_REWRITER_SUSPECTED"
    assert "contain-localhost-rewriter" in card["recommended_next_command"]
    assert card["policy_action"] == "escalate"
    assert card["dry_run"] is True


def test_dead_proxy_outranks_path() -> None:
    card = load_operator_incident_fixture(FIXTURES / "dead_proxy.json")
    assert card["primary_class"] == "DEAD_PROXY_CONFIG"
    assert "proxy-guardian" in card["recommended_next_command"]


def test_ipv6_false_clear_when_proxy_off() -> None:
    card = load_operator_incident_fixture(FIXTURES / "ipv6_broken.json")
    assert card["primary_class"] == "IPV6_BROKEN_IPV4_OK"
    assert "false_clear_rate" in card["sli_hints"]
    assert "dual_stack_path_success" in card["sli_hints"]
    assert any("IPv4-ok + IPv6-fail" in lim for lim in card["limitations"])
    assert "network-path-health" in card["recommended_next_command"]


def test_happy_eyeballs_outranks_browser_quic() -> None:
    card = load_operator_incident_fixture(FIXTURES / "quic_stall.json")
    assert card["primary_class"] == "HAPPY_EYEBALLS_STALL"
    assert "BROWSER_QUIC_STALL" in card["contributing_classes"]


def test_healthy_compose() -> None:
    card = load_operator_incident_fixture(FIXTURES / "healthy.json")
    assert card["primary_class"] in {"PATH_OK", "NO_PROXY", "HEALTHY", "NO_PROXY_DIRECT_OK"}
    assert card["policy_action"] == "observe"
    assert card["limitations"]


def test_limitations_never_dropped() -> None:
    extra = ["source-specific limitation alpha"]
    card = compose_operator_incident_card(
        proxy={"classification": "NO_PROXY", "limitations": extra},
        path_health={"classification": "IPV6_BROKEN_IPV4_OK", "limitations": ["path lim"]},
    )
    blob = " ".join(card["limitations"])
    assert "source-specific limitation alpha" in blob
    assert "path lim" in blob
    assert "this card never" in blob.lower()


def test_card_never_sets_executed() -> None:
    card = compose_operator_incident_card(
        proxy={"classification": "DEAD_PROXY_CONFIG"},
        rewriter={"match": True},
    )
    assert card.get("governance", {}).get("execution_authority") == "preview_only"
    assert card["dry_run"] is True


def test_src_cli_fixture(capsys) -> None:
    code = main(
        [
            "operator-incident",
            "--fixture",
            str(FIXTURES / "ipv6_broken.json"),
            "--format",
            "json",
        ]
    )
    assert code == 0
    out = capsys.readouterr().out
    assert "IPV6_BROKEN_IPV4_OK" in out
    assert "limitations" in out


def test_empty_sources_insufficient() -> None:
    card = compose_operator_incident_card()
    assert card["primary_class"] == "INSUFFICIENT_DATA"
    assert card["confidence"] <= 0.3
