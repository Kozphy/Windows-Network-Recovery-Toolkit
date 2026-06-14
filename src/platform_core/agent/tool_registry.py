"""Safe tool registry — maps tool names to evidence-only adapters."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from pydantic import BaseModel, Field

DEFAULT_CS1_FIXTURE = Path("case_studies/cs1_wininet_proxy_drift/fixture.json")


class ToolContext(BaseModel):
    url: str | None = None
    fixture_path: str | None = None
    dry_run: bool = True
    extra: dict[str, Any] = Field(default_factory=dict)


class ToolResult(BaseModel):
    tool: str
    evidence: dict[str, Any] = Field(default_factory=dict)
    limitations: list[str] = Field(default_factory=list)
    confidence_display: str = ""
    proof_status: str | None = None
    correlation_only: list[str] = Field(default_factory=list)
    supported_by_proof: list[str] = Field(default_factory=list)


def _load_fixture(ctx: ToolContext) -> dict[str, Any]:
    path = Path(ctx.fixture_path) if ctx.fixture_path else DEFAULT_CS1_FIXTURE
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def tool_proxy_status(ctx: ToolContext) -> ToolResult:
    """Read-only WinINET proxy snapshot."""
    fixture = _load_fixture(ctx)
    state = fixture.get("proxy_state") or {}
    classification = fixture.get("classification") or {}
    if state:
        return ToolResult(
            tool="proxy_status",
            evidence={
                "wininet_proxy_enabled": state.get("wininet_proxy_enabled"),
                "wininet_proxy_server": state.get("wininet_proxy_server"),
                "classification": classification.get("primary_classification"),
            },
            limitations=list(classification.get("limitations") or [
                "Observation is not proof.",
                "Listener correlation is not registry-writer proof.",
            ]),
            confidence_display=f"ordinal {classification.get('confidence', 0.0):.2f} (heuristic score, not probability)",
            correlation_only=["listener_found"] if fixture.get("proxy_owner") else [],
        )
    # TODO: connect live path — windows_network_toolkit.proxy_state.collect_proxy_state_model
    return ToolResult(
        tool="proxy_status",
        evidence={"note": "No fixture; live collection requires Windows host."},
        limitations=["Live proxy_status without fixture not wired in agent adapter yet."],
    )


def tool_diagnose_proxy(ctx: ToolContext) -> ToolResult:
    """Structured proxy proof envelope."""
    fixture = _load_fixture(ctx)
    proof = fixture.get("proof") or {}
    classification = fixture.get("classification") or {}
    if proof:
        conclusion = proof.get("conclusion") or {}
        supported = [
            a["name"]
            for a in proof.get("proof_attempts", [])
            if isinstance(a, dict) and a.get("status") in ("supported", "passed")
        ]
        return ToolResult(
            tool="diagnose_proxy",
            evidence={
                "observation": proof.get("observation"),
                "hypothesis": proof.get("hypothesis"),
                "proof_attempts": proof.get("proof_attempts"),
                "conclusion": conclusion,
                "classification": classification.get("primary_classification"),
            },
            limitations=list(proof.get("limitations") or []),
            confidence_display=f"ordinal {conclusion.get('confidence', 0.0):.2f} (heuristic score, not probability)",
            proof_status=str(conclusion.get("status") or "unknown"),
            supported_by_proof=supported,
            correlation_only=["localhost_listener_check"],
        )
    # TODO: connect live path — windows_network_toolkit.proof.run_diagnose_proof
    return ToolResult(
        tool="diagnose_proxy",
        evidence={},
        limitations=["Provide fixture_path for fixture-safe diagnose_proxy."],
    )


def tool_tls_proof(ctx: ToolContext) -> ToolResult:
    url = ctx.url or "https://example.com"
    fixture = _load_fixture(ctx)
    tls = fixture.get("tls_proof")
    if tls:
        return ToolResult(
            tool="tls_proof",
            evidence={"url": url, **tls},
            limitations=list(tls.get("limitations") or [
                "TLS path contrast supports configuration diagnosis; it does not prove MITM.",
            ]),
            confidence_display=str(tls.get("confidence_display") or "ordinal 0.5 (heuristic score, not probability)"),
            proof_status=tls.get("conclusion_status"),
        )
    return ToolResult(
        tool="tls_proof",
        evidence={
            "url": url,
            "status": "fixture_required",
            "message": "TLS proof adapter stub — inject tls_proof in fixture or call CLI tls-proof.",
        },
        limitations=[
            "No live TLS probe in agent layer without fixture.",
            "Certificate observation is not malware proof.",
        ],
    )


def tool_website_risk(ctx: ToolContext) -> ToolResult:
    url = ctx.url or "https://example.com"
    fixture = _load_fixture(ctx)
    risk = fixture.get("website_risk")
    if risk:
        return ToolResult(
            tool="website_risk",
            evidence={"url": url, **risk},
            limitations=list(risk.get("limitations") or [
                "Heuristic website risk score is for review — not an automated block verdict.",
            ]),
            confidence_display=str(risk.get("confidence_display") or "ordinal 0.5 (heuristic score, not probability)"),
        )
    return ToolResult(
        tool="website_risk",
        evidence={"url": url, "risk_tier": "unknown", "note": "fixture_required"},
        limitations=["Website risk scoring requires fixture or live engine wiring."],
    )


def tool_evidence_report(ctx: ToolContext) -> ToolResult:
    fixture = _load_fixture(ctx)
    classification = fixture.get("classification") or {}
    proof = fixture.get("proof") or {}
    return ToolResult(
        tool="evidence_report",
        evidence={
            "case_id": fixture.get("case_id"),
            "title": fixture.get("title"),
            "classification": classification,
            "proof_summary": {
                "hypothesis": proof.get("hypothesis"),
                "conclusion": proof.get("conclusion"),
            },
            "policy_decision": fixture.get("policy_decision"),
        },
        limitations=list(classification.get("limitations") or []) + list(proof.get("limitations") or []),
        confidence_display=f"ordinal {classification.get('confidence', 0.0):.2f} (heuristic score, not probability)",
        proof_status=(proof.get("conclusion") or {}).get("status"),
    )


def tool_remediation_preview(ctx: ToolContext) -> ToolResult:
    """Preview-only remediation — never mutates registry from agent layer."""
    fixture = _load_fixture(ctx)
    policy = fixture.get("policy_decision") or {}
    effective_dry_run = True  # agent layer always preview-only
    return ToolResult(
        tool="remediation_preview",
        evidence={
            "action": policy.get("action") or "DISABLE_WININET_PROXY",
            "outcome": "PREVIEW_ONLY",
            "dry_run": effective_dry_run,
            "requires_confirmation": True,
            "confirmation_token": policy.get("confirmation_token") or "DISABLE_WININET_PROXY",
            "planned_changes": [
                "Set WinINET ProxyEnable to 0 (preview only)",
                "Clear ProxyServer if policy allows (preview only)",
            ],
            "no_changes_made": True,
        },
        limitations=[
            "Agent layer never executes registry mutations.",
            "Policy permission is not a safety guarantee.",
            "Typed confirmation and rollback plan required for live apply via CLI.",
        ],
        proof_status="preview_only",
    )


def tool_audit_verify(ctx: ToolContext) -> ToolResult:
    from src.platform_core.governance.chain_of_custody import verify_chain

    audit_path = ctx.extra.get("audit_path")
    if audit_path:
        path = Path(str(audit_path))
        if path.is_file():
            records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
            ok, msg = verify_chain(records)
            return ToolResult(
                tool="audit_verify",
                evidence={"ok": ok, "message": msg, "record_count": len(records)},
                limitations=["Hash chain verifies integrity, not correctness of decisions."],
            )
    return ToolResult(
        tool="audit_verify",
        evidence={"ok": True, "message": "no chain file provided — stub ok for empty audit"},
        limitations=["Provide audit_path in extra for live chain verification."],
    )


SAFE_TOOLS: dict[str, Callable[[ToolContext], ToolResult]] = {
    "proxy_status": tool_proxy_status,
    "diagnose_proxy": tool_diagnose_proxy,
    "tls_proof": tool_tls_proof,
    "website_risk": tool_website_risk,
    "evidence_report": tool_evidence_report,
    "remediation_preview": tool_remediation_preview,
    "audit_verify": tool_audit_verify,
}

BLOCKED_TOOL_NAMES = frozenset({
    "shell_exec",
    "kill_process",
    "reset_firewall",
    "disable_adapter",
    "registry_mutation",
})


def invoke_tool(name: str, ctx: ToolContext) -> ToolResult:
    if name in BLOCKED_TOOL_NAMES:
        raise ValueError(f"blocked tool: {name}")
    fn = SAFE_TOOLS.get(name)
    if fn is None:
        raise KeyError(f"unknown safe tool: {name}")
    return fn(ctx)
