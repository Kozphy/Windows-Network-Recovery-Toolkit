from pathlib import Path

from app.audit import HashChainAuditLog
from app.engine import analyze
from app.models import Criterion, DecisionRequest, EvidenceItem, EvidenceKind, Option


def sample_request() -> DecisionRequest:
    return DecisionRequest(
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
    assert result.requires_human_approval is True
    assert result.status == "pending_human_review"
    assert result.assumptions
    assert result.unknowns


def test_hash_chain_detects_tampering(tmp_path: Path) -> None:
    path = tmp_path / "audit.jsonl"
    log = HashChainAuditLog(path)
    log.append("one", {"value": 1})
    log.append("two", {"value": 2})
    assert log.verify() == (True, 2)

    text = path.read_text(encoding="utf-8").replace('"value":1', '"value":9', 1)
    path.write_text(text, encoding="utf-8")
    valid, _ = log.verify()
    assert valid is False
