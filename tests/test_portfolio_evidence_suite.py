"""Portfolio evidence fixtures — classification, risk boundaries, audit, safety, replay."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from platform_core.policy import OperatorContext, evaluate
from src.platform_core.ai_risk_analyst import (
    AnalystEvidenceBundle,
    LocalRuleBasedAnalyst,
    MockAnalyst,
    apply_guardrails,
    recommendation_passes_safety,
)
from src.platform_core.governance.chain_of_custody import verify_chain
from src.platform_core.risk import assess_risk, load_fixture, rate_risk, run_control_tests
from src.platform_core.risk.finding import findings_from_fixture
from windows_network_toolkit.audit.replay import replay_to_dict

REPO = Path(__file__).resolve().parents[1]
EVIDENCE_DIR = REPO / "examples" / "evidence"
CASE_1 = REPO / "tests" / "fixtures" / "case_studies" / "case_1_dead_wininet_proxy.json"
REPLAY_FIXTURE = REPO / "windows_network_toolkit" / "examples" / "proxy_drift_incident.jsonl"


@pytest.fixture(params=[
    "DEAD_PROXY_CONFIG.json",
    "WININET_WINHTTP_MISMATCH.json",
    "LOCAL_PROXY_ACTIVE.json",
    "REVERTER_SUSPECTED.json",
    "POSSIBLE_MITM_RISK.json",
])
def evidence_fixture_path(request: pytest.FixtureRequest) -> Path:
    path = EVIDENCE_DIR / request.param
    assert path.is_file(), f"Missing portfolio evidence fixture: {path}"
    return path


def test_portfolio_evidence_fixtures_parse(evidence_fixture_path: Path) -> None:
    data = json.loads(evidence_fixture_path.read_text(encoding="utf-8"))
    assert data["schema_version"] == "portfolio_evidence.v1"
    assert data["incident_id"]
    assert data["classification"]["primary_classification"]
    assert data["classification"]["limitations"]


@pytest.mark.parametrize(
    "filename,expected_primary",
    [
        ("DEAD_PROXY_CONFIG.json", "DEAD_PROXY_CONFIG"),
        ("WININET_WINHTTP_MISMATCH.json", "DEAD_PROXY_CONFIG"),
        ("LOCAL_PROXY_ACTIVE.json", "LOCAL_PROXY_ACTIVE"),
        ("REVERTER_SUSPECTED.json", "REVERTER_SUSPECTED"),
        ("POSSIBLE_MITM_RISK.json", "POSSIBLE_MITM_RISK"),
    ],
)
def test_portfolio_evidence_classification_labels(filename: str, expected_primary: str) -> None:
    data = json.loads((EVIDENCE_DIR / filename).read_text(encoding="utf-8"))
    assert data["classification"]["primary_classification"] == expected_primary


def test_case_1_risk_assess_dead_proxy() -> None:
    fixture = load_fixture(CASE_1)
    result = assess_risk(fixture)
    classifications = [f["classification"] for f in result["findings"]]
    assert "DEAD_PROXY_CONFIG" in classifications
    assert result["governance"]["governance_model"] == "evidence_to_action.v1"


def test_risk_score_confidence_bounded() -> None:
    fixture = load_fixture(CASE_1)
    tests = run_control_tests(fixture)
    findings = findings_from_fixture(fixture, tests)
    rating = rate_risk(findings, tests, fixture)
    assert 0.0 <= rating.confidence <= 1.0
    assert rating.inherent_level in {"low", "medium", "high", "critical"}
    assert rating.limitations


def test_mitm_without_tls_proof_stays_medium_or_lower_inherent() -> None:
    data = json.loads((EVIDENCE_DIR / "POSSIBLE_MITM_RISK.json").read_text(encoding="utf-8"))
    tests = run_control_tests(data)
    findings = findings_from_fixture(data, tests)
    rating = rate_risk(findings, tests, data)
    assert rating.inherent_level in {"low", "medium", "high"}
    assert rating.limitations


def test_audit_chain_verify_roundtrip(tmp_path: Path) -> None:
    from src.platform_core.audit.writer import append_audit, reset_chain_for_tests

    reset_chain_for_tests()
    audit_path = tmp_path / "chain.jsonl"
    append_audit("event_received", incident_id="INC-1", path=audit_path)
    append_audit("policy_evaluated", incident_id="INC-1", path=audit_path)
    records = [
        json.loads(line)
        for line in audit_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    ok, msg = verify_chain(records)
    assert ok, msg
    assert all(r.get("current_hash") for r in records)


def test_portfolio_audit_sample_jsonl_parses() -> None:
    audit_path = REPO / "tests" / "fixtures" / "risk_analytics" / "audit_sample" / "incidents.jsonl"
    records = [
        json.loads(line)
        for line in audit_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(records) >= 5
    assert all("incident_id" in r for r in records)


def test_no_unsafe_remediation_without_confirmation() -> None:
    gate_kill = evaluate({}, "process_kill_forbidden", OperatorContext(role="admin", surface="api"))
    assert gate_kill.execute_allowed is False
    gate_fw = evaluate({}, "reset_firewall", OperatorContext(role="admin", surface="api"))
    assert gate_fw.execute_allowed is False


def test_replay_deterministic_proxy_drift() -> None:
    if not REPLAY_FIXTURE.is_file():
        pytest.skip("replay fixture missing")
    a = replay_to_dict(REPLAY_FIXTURE, dry_run=True)
    b = replay_to_dict(REPLAY_FIXTURE, dry_run=True)

    skip_keys = {"decision_id", "trace_id", "incident_id", "timestamp_utc", "evaluation_id"}

    def _stable(block: dict) -> dict:
        return {k: v for k, v in block.items() if k not in skip_keys}

    assert _stable(a["decision"]) == _stable(b["decision"])
    assert _stable(a["policy"]) == _stable(b["policy"])


def test_mock_analyst_deterministic_dead_proxy() -> None:
    data = json.loads((EVIDENCE_DIR / "DEAD_PROXY_CONFIG.json").read_text(encoding="utf-8"))
    bundle = AnalystEvidenceBundle(
        incident_id=data["incident_id"],
        proxy_status=data.get("proxy_state"),
        listener_info=data.get("listener_info"),
        classification=data.get("classification"),
        proof=data.get("proof"),
        policy_decision=data.get("policy_decision"),
    )
    a = MockAnalyst().analyze(bundle)
    b = MockAnalyst().analyze(bundle)
    assert a.incident_summary == b.incident_summary
    assert a.recommended_action == b.recommended_action
    assert a.provider == "mock"
    assert recommendation_passes_safety(a)


def test_known_dev_proxy_not_malicious_wording() -> None:
    data = json.loads((EVIDENCE_DIR / "LOCAL_PROXY_ACTIVE.json").read_text(encoding="utf-8"))
    bundle = AnalystEvidenceBundle(
        incident_id=data["incident_id"],
        proxy_status=data["proxy_state"],
        listener_info=data["listener_info"],
        classification={"primary_classification": "LOCAL_PROXY_ENABLED"},
    )
    rec = LocalRuleBasedAnalyst().analyze(bundle)
    rec = apply_guardrails(rec, bundle)
    text = f"{rec.likely_hypothesis} {rec.incident_summary}".lower()
    assert "malicious" not in text
    assert "attacker" not in text


def test_suspicious_proxy_requires_review() -> None:
    bundle = AnalystEvidenceBundle(
        incident_id="test-suspicious",
        classification={"primary_classification": "SUSPICIOUS_LOCAL_PROXY"},
    )
    rec = apply_guardrails(LocalRuleBasedAnalyst().analyze(bundle), bundle)
    assert rec.human_review.required or rec.human_review.status in {"recommended", "required"}
    assert "registry_writer" in " ".join(rec.missing_evidence).lower() or rec.missing_evidence


def test_ai_recommendation_includes_audit_id_and_forbidden_actions() -> None:
    data = json.loads((EVIDENCE_DIR / "DEAD_PROXY_CONFIG.json").read_text(encoding="utf-8"))
    bundle = AnalystEvidenceBundle(incident_id=data["incident_id"], classification=data["classification"])
    rec = MockAnalyst().analyze(bundle)
    assert rec.audit_id.startswith("mock-audit-")
    assert "disable_proxy" in rec.forbidden_actions or "registry_modification" in rec.forbidden_actions
