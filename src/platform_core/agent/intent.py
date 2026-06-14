"""Rule-based natural-language intent classification (no external LLM)."""

from __future__ import annotations

import re
from enum import StrEnum


class AgentIntent(StrEnum):
    DIAGNOSE_PROXY = "DIAGNOSE_PROXY"
    CHECK_TLS = "CHECK_TLS"
    SCORE_WEBSITE_RISK = "SCORE_WEBSITE_RISK"
    GENERATE_EVIDENCE_REPORT = "GENERATE_EVIDENCE_REPORT"
    PREVIEW_REMEDIATION = "PREVIEW_REMEDIATION"
    VERIFY_AUDIT_CHAIN = "VERIFY_AUDIT_CHAIN"
    UNKNOWN = "UNKNOWN"


_PROXY_PATTERNS = (
    r"err_proxy",
    r"proxy broken",
    r"proxy drift",
    r"cannot connect",
    r"can't connect",
    r"browser cannot",
    r"browser can't",
    r"wininet",
    r"dead proxy",
    r"localhost proxy",
    r"proxy connection failed",
    r"proxy misconfig",
)

_TLS_PATTERNS = (
    r"\btls\b",
    r"certificate",
    r"\bmitm\b",
    r"root ca",
    r"ssl error",
    r"cert chain",
)

_RISK_PATTERNS = (
    r"website risk",
    r"phishing",
    r"is this url risky",
    r"url risky",
    r"score.*url",
    r"risky site",
)

_REPORT_PATTERNS = (
    r"evidence report",
    r"audit report",
    r"make report",
    r"generate report",
    r"incident report",
)

_REMEDIATION_PATTERNS = (
    r"\bfix it\b",
    r"\brepair\b",
    r"disable proxy",
    r"turn off proxy",
    r"remove proxy",
    r"remediation preview",
    r"preview fix",
)

_AUDIT_PATTERNS = (
    r"verify audit",
    r"hash chain",
    r"audit chain",
    r"chain integrity",
)


def classify_intent(message: str) -> AgentIntent:
    """Classify operator message into a supported intent using ordered rules."""
    text = (message or "").strip().lower()
    if not text:
        return AgentIntent.UNKNOWN

    if any(re.search(p, text) for p in _REMEDIATION_PATTERNS):
        return AgentIntent.PREVIEW_REMEDIATION
    if any(re.search(p, text) for p in _AUDIT_PATTERNS):
        return AgentIntent.VERIFY_AUDIT_CHAIN
    if any(re.search(p, text) for p in _REPORT_PATTERNS):
        return AgentIntent.GENERATE_EVIDENCE_REPORT
    if any(re.search(p, text) for p in _RISK_PATTERNS):
        return AgentIntent.SCORE_WEBSITE_RISK
    if any(re.search(p, text) for p in _TLS_PATTERNS):
        return AgentIntent.CHECK_TLS
    if any(re.search(p, text) for p in _PROXY_PATTERNS):
        return AgentIntent.DIAGNOSE_PROXY

    return AgentIntent.UNKNOWN


INTENT_TO_TOOL: dict[AgentIntent, str | None] = {
    AgentIntent.DIAGNOSE_PROXY: "diagnose_proxy",
    AgentIntent.CHECK_TLS: "tls_proof",
    AgentIntent.SCORE_WEBSITE_RISK: "website_risk",
    AgentIntent.GENERATE_EVIDENCE_REPORT: "evidence_report",
    AgentIntent.PREVIEW_REMEDIATION: "remediation_preview",
    AgentIntent.VERIFY_AUDIT_CHAIN: "audit_verify",
    AgentIntent.UNKNOWN: None,
}
