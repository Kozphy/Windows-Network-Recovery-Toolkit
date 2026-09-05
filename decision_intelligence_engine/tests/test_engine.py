from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt
from fastapi.security import HTTPAuthorizationCredentials

from app.audit import HashChainAuditLog
from app.auth import get_principal
from app.engine import analyze
from app.evaluation import CalibrationPoint, CalibrationRequest, evaluate_calibration
from app.models import Criterion, DecisionRequest, EvidenceItem, EvidenceKind, Option
from app.policy import approval_allowed, load_policy
from app.store import DecisionStore


def sample_request() -> DecisionRequest:
    return DecisionRequest(
        requester="requester@example.com",
        domain="technology-risk",
        question="Which implementation option should we choose?",
        evidence=[
            EvidenceItem(statement="Option A passed replay tests", kind=EvidenceKind.FACT, confidence=0.9),
            EvidenceItem(statement="Traffic may double next quarter", kind=EvidenceKind.ASSUMPTION, confidence=0.5),
            EvidenceItem(statement="Exact production latency is unknown", kind=EvidenceKind.UNKNOWN, confidence=0.2),
        ],
        criteria=[Criterion(name="value", weight=0.6), Criterion(name="reliability", weight=0.4)],
        options=[
            Option(name="A", scores={"value": 0.9, "reliability": 0.8}, risk=0.2, uncertainty=0.2),
            Option(name="B", scores={"value": 0.7, "reliability": 0.7}, risk=0.3, uncertainty=0.4),
        ],
    )


def test_recommendation_requires_human_approval() -> None:
    result = analyze(sample_request())
    assert result.recommended_option == "A"
    assert result.requester == "requester@example.com"
    assert result.requires_human_approval is True
    assert result.status == "pending_human_review"
    assert result.assumptions
    assert result.unknowns


def test_versioned_policy_blocks_low_evidence_approval() -> None:
    policy = load_policy()
    assert policy.version == "1.0.0"
    request = sample_request().model_copy(update={"evidence": []})
    result = analyze(request, policy=policy)
    assert "LOW_EVIDENCE_COVERAGE" in result.policy_flags
    allowed, reason = approval_allowed(result, policy=policy)
    assert allowed is False
    assert "1.0.0" in str(reason)


def test_sql_store_survives_object_recreation(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'decisions.db'}"
    result = analyze(sample_request())
    DecisionStore(database_url).save_recommendation(result)
    loaded = DecisionStore(database_url).get_recommendation(result.decision_id)
    assert loaded is not None
    assert loaded.decision_id == result.decision_id
    assert loaded.recommended_option == result.recommended_option


def test_hash_chain_detects_tampering_and_supports_replay(tmp_path: Path) -> None:
    path = tmp_path / "audit.jsonl"
    log = HashChainAuditLog(path)
    log.append("recommendation_created", {"decision_id": "d-1", "value": 1})
    log.append("human_decision_recorded", {"decision_id": "d-1", "value": 2})
    log.append("other", {"decision_id": "d-2", "value": 3})
    assert log.verify() == (True, 3)
    assert len(log.replay("d-1")) == 2

    text = path.read_text(encoding="utf-8").replace('"value":1', '"value":9', 1)
    path.write_text(text, encoding="utf-8")
    valid, _ = log.verify()
    assert valid is False


def test_calibration_metrics_are_deterministic() -> None:
    report = evaluate_calibration(
        CalibrationRequest(
            points=[
                CalibrationPoint(confidence=0.9, success=True),
                CalibrationPoint(confidence=0.8, success=True),
                CalibrationPoint(confidence=0.2, success=False),
                CalibrationPoint(confidence=0.6, success=False),
            ],
            bins=5,
        )
    )
    assert report.samples == 4
    assert 0.0 <= report.brier_score <= 1.0
    assert 0.0 <= report.expected_calibration_error <= 1.0


def test_signed_jwt_identity_and_roles(monkeypatch) -> None:
    monkeypatch.setenv("DI_AUTH_MODE", "jwt")
    monkeypatch.setenv("DI_JWT_SECRET", "test-secret")
    monkeypatch.setenv("DI_JWT_ISSUER", "https://issuer.example")
    monkeypatch.setenv("DI_JWT_AUDIENCE", "decision-engine")
    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {
            "sub": "alice@example.com",
            "roles": ["requester", "auditor"],
            "iss": "https://issuer.example",
            "aud": "decision-engine",
            "iat": now,
            "exp": now + timedelta(minutes=5),
        },
        "test-secret",
        algorithm="HS256",
    )
    principal = get_principal(
        HTTPAuthorizationCredentials(scheme="Bearer", credentials=token),
        None,
        None,
    )
    assert principal.subject == "alice@example.com"
    assert principal.roles == frozenset({"requester", "auditor"})
