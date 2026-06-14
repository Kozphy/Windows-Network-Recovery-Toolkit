"""Human-readable agent responses with epistemic guardrails."""

from __future__ import annotations

from src.platform_core.agent.intent import AgentIntent
from src.platform_core.agent.tool_registry import ToolResult


def build_answer(intent: AgentIntent, tool: ToolResult | None, *, allowed: bool, reason: str) -> str:
    if not allowed:
        return (
            f"Request denied: {reason}. "
            "No evidence tools were executed. "
            "Contact an operator or admin if you need elevated access."
        )

    if intent == AgentIntent.UNKNOWN or tool is None:
        return (
            "I could not map your question to a supported evidence tool. "
            "Try asking about proxy diagnosis, TLS proof, website risk, evidence reports, "
            "remediation preview, or audit verification. "
            "I will not execute repairs or shell commands automatically."
        )

    parts: list[str] = []

    if intent == AgentIntent.DIAGNOSE_PROXY:
        classification = (tool.evidence.get("classification") or tool.evidence.get("conclusion") or {})
        if isinstance(classification, dict):
            primary = classification.get("primary_classification") or classification.get("status")
        else:
            primary = classification
        parts.append(
            f"Evidence suggests a proxy-related configuration issue ({primary or 'see evidence'}). "
            "This supports a browser-path failure hypothesis when proof status is supported."
        )
        if tool.proof_status == "supported":
            parts.append("Structured proof supports the dead or mismatched proxy hypothesis.")
        else:
            parts.append("Proof is incomplete — treat findings as observations until proof completes.")

    elif intent == AgentIntent.CHECK_TLS:
        parts.append(
            "TLS/certificate evidence was collected for review. "
            "Path contrast may support configuration diagnosis."
        )

    elif intent == AgentIntent.SCORE_WEBSITE_RISK:
        parts.append(
            "Website risk heuristics are for analyst review — not an automated block verdict."
        )

    elif intent == AgentIntent.GENERATE_EVIDENCE_REPORT:
        parts.append("Evidence report assembled from structured fixture or collected signals.")

    elif intent == AgentIntent.PREVIEW_REMEDIATION:
        parts.append(
            "Remediation preview generated. Registry mutation remains blocked from the agent layer. "
            "Live apply requires existing policy gates, rollback plan, and typed confirmation via CLI."
        )

    elif intent == AgentIntent.VERIFY_AUDIT_CHAIN:
        ok = tool.evidence.get("ok")
        parts.append(f"Audit chain verification result: ok={ok}.")

    if tool.correlation_only:
        parts.append(
            f"Correlation-only signals (not causation proof): {', '.join(tool.correlation_only)}."
        )

    parts.append("This does not prove malware or MITM.")
    parts.append(f"Safe next step: {recommended_next_action(intent, tool)}.")

    return " ".join(parts)


def recommended_next_action(intent: AgentIntent, tool: ToolResult | None) -> str:
    if intent == AgentIntent.DIAGNOSE_PROXY:
        if tool and tool.proof_status == "supported":
            return "generate a remediation preview (operator role) — do not auto-execute"
        return "collect additional evidence with diagnose --proof"
    if intent == AgentIntent.PREVIEW_REMEDIATION:
        return "review preview output; apply via CLI with typed confirmation if policy allows"
    if intent == AgentIntent.CHECK_TLS:
        return "compare TLS path evidence with proxy configuration"
    if intent == AgentIntent.SCORE_WEBSITE_RISK:
        return "escalate to security analyst with limitations documented"
    if intent == AgentIntent.GENERATE_EVIDENCE_REPORT:
        return "attach report to incident ticket"
    if intent == AgentIntent.VERIFY_AUDIT_CHAIN:
        return "investigate chain break if verification failed"
    return "rephrase your question using supported diagnostic intents"
