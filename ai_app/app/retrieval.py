from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class KnowledgeItem:
    source: str
    text: str


KNOWLEDGE = [
    KnowledgeItem("runbook/proxy-drift", "Proxy drift can cause an endpoint to appear online while application traffic fails."),
    KnowledgeItem("runbook/tls-path", "TLS path mismatches should be validated before proposing certificate or trust-store remediation."),
    KnowledgeItem("control/human-approval", "State-changing remediation must be policy checked and explicitly approved before execution."),
]


def retrieve(query: str, limit: int = 3) -> list[KnowledgeItem]:
    """Small deterministic retrieval baseline; replace with hybrid/vector retrieval later."""
    tokens = {token.strip(".,:;!?()[]{}\"").lower() for token in query.split() if token.strip()}
    ranked: list[tuple[int, KnowledgeItem]] = []
    for item in KNOWLEDGE:
        haystack = item.text.lower()
        score = sum(1 for token in tokens if len(token) > 2 and token in haystack)
        ranked.append((score, item))
    ranked.sort(key=lambda pair: pair[0], reverse=True)
    return [item for score, item in ranked if score > 0][:limit]
