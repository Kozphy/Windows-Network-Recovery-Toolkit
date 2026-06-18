"""Extended CI safety contracts for governance platform guarantees."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from platform_core.policy import OperatorContext, evaluate, validate_confirmation_phrase
from platform_core.remediation_registry import get_remediation_action
from src.platform_core.ai_risk_analyst.guardrails import enforce_advisory_only
from src.platform_core.audit.writer import append_audit, reset_chain_for_tests
from src.platform_core.governance.chain_of_custody import verify_chain
from src.platform_core.governance.risk_decision_record import build_risk_decision_record

REPO = Path(__file__).resolve().parents[1]
CASE_1 = REPO / "tests" / "fixtures" / "case_studies" / "case_1_dead_wininet_proxy.json"


@pytest.mark.parametrize(
    "action",
    ["process_kill_forbidden", "adapter_disable_forbidden", "reset_firewall", "arbitrary_command_forbidden"],
)
def test_forbidden_actions_never_execute(action: str) -> None:
    gate = evaluate({}, action, OperatorContext(role="admin", surface="cli"))
    assert gate.execute_allowed is False


def test_registry_mutation_requires_typed_confirmation_phrase() -> None:
    for key in ("reset_proxy", "reset_dns"):
        defn = get_remediation_action(key)
        assert defn is not None
        assert defn.requires_confirmation
        assert validate_confirmation_phrase(key, "") is False
        assert validate_confirmation_phrase(key, defn.confirmation_phrase) is True


def test_dry_run_default_in_risk_decision_record() -> None:
    fixture = json.loads(CASE_1.read_text(encoding="utf-8"))
    record = build_risk_decision_record(fixture)
    assert record.execution_authority == "preview_only"


def test_ai_output_cannot_grant_execution_authority() -> None:
    out = enforce_advisory_only({"execution_authority": "full_auto", "summary": "apply now"})
    assert out["execution_authority"] in ("preview_only", "human_required", "blocked")


def test_audit_append_only_chain_detects_tampering(tmp_path: Path) -> None:
    reset_chain_for_tests()
    path = tmp_path / "audit.jsonl"
    r1 = append_audit("event_received", incident_id="i1", path=path)
    r2 = append_audit("decision_created", incident_id="i1", path=path)
    ok, _ = verify_chain([r1.model_dump(), r2.model_dump()])
    assert ok is True
    tampered = dict(r2.model_dump())
    tampered["payload"] = {"tampered": True}
    ok2, msg2 = verify_chain([r1.model_dump(), tampered])
    assert ok2 is False
    assert msg2
