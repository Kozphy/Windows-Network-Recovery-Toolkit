"""High-level policy router for Endpoint Reliability Platform demos.

Wraps :func:`~platform_core.policy.evaluate` with ergonomic **verb** projections plus optional declarative rule
hints loaded from ``config/platform_policy.example.json``. Does **not** replace :mod:`platform_core.remediation_registry`
— unknown actions remain registry-denied.

Decision verbs map to remediation posture:
    * ``allow`` — live execute may proceed downstream when RBAC + confirmation gates also pass (rare standalone signal).
    * ``alert`` — surface to operator dashboards without implying execute permission.
    * ``block`` — deny execution unconditionally for this posture (forbidden/high shell patterns).
    * ``preview_only`` — operator-tier may stage previews; execute denied.
    * ``require_confirmation`` — admin path still needs typed phrases from registry definitions.

Input assumptions:
    ``signal_bundle`` dictionaries may carry ``proxy_server``, ``unsigned_path_hint``, ``summary`` placeholders
    from fixtures — tagging results surface in ``applied_rules`` alongside structured policy reasons.

Side effects:
    File load helpers read JSON once per path string (callers cache if hot).

See Also:
    ``docs/rbac_and_remediation.md``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from platform_core.policy import OperatorContext, SignalSnapshot, evaluate as evaluate_structured

PlatformDecisionVerb = Literal["allow", "alert", "block", "preview_only", "require_confirmation"]

@dataclass(frozen=True)
class PlatformPolicyHints:
    """Declarative knobs mirrored from optional JSON/YAML bundles for interviews."""

    allow_developer_proxy_ports: list[int]
    localhost_proxy_requires_alert: bool
    unsigned_path_alert_only: bool
    rollback_requires_confirmation: bool


DEFAULT_HINTS = PlatformPolicyHints(
    allow_developer_proxy_ports=[7890, 8888],
    localhost_proxy_requires_alert=True,
    unsigned_path_alert_only=True,
    rollback_requires_confirmation=True,
)


def load_policy_hints(path: str | Path | None) -> PlatformPolicyHints:
    """Hydrate hints from JSON on disk — missing file yields :data:`DEFAULT_HINTS`.

    Raises:
        json.JSONDecodeError: Propagates when malformed (callers validate in demos).
    """
    if not path:
        return DEFAULT_HINTS
    p = Path(path)
    if not p.is_file():
        return DEFAULT_HINTS
    raw = json.loads(p.read_text(encoding="utf-8"))
    ports = raw.get("developer_proxy_allowlist_ports") or raw.get("allow_developer_proxy_ports") or []
    return PlatformPolicyHints(
        allow_developer_proxy_ports=[int(x) for x in ports],
        localhost_proxy_requires_alert=bool(raw.get("localhost_proxy_requires_alert", True)),
        unsigned_path_alert_only=bool(raw.get("unsigned_path_alert_only", True)),
        rollback_requires_confirmation=bool(raw.get("rollback_requires_confirmation", True)),
    )


def _verb_from_structured(exec_allowed: bool, preview_allowed: bool, reason_codes: list[str]) -> PlatformDecisionVerb:
    if any("forbidden" in r or "arbitrary" in r for r in reason_codes):
        return "block"
    if exec_allowed:
        return "allow"
    if preview_allowed and any("confirmation" in r for r in reason_codes):
        return "require_confirmation"
    if preview_allowed:
        return "preview_only"
    return "alert"


def evaluate_route_decision(
    *,
    remediation_action: str | None,
    operator_role: str,
    surface: Literal["api", "cli", "dashboard"] = "api",
    signal_bundle: dict[str, Any] | None = None,
    hints: PlatformPolicyHints | None = None,
) -> tuple[PlatformDecisionVerb, dict[str, Any]]:
    """Return ``(verb, detail_dict)`` fusing structured policy + heuristic signal tagging.

    The ``detail_dict`` includes upstream ``StructuredPolicyDecision`` dump plus ``applied_rules`` string keys
    documenting which portfolio hints influenced alert posture (never bypasses forbidden registry tiers).
    """
    hc = hints or DEFAULT_HINTS
    applied_rules: list[str] = []

    bundle = dict(signal_bundle or {})

    prox = str(bundle.get("proxy_server") or "").lower()
    if "127.0.0.1" in prox or "localhost" in prox:
        if hc.localhost_proxy_requires_alert:
            applied_rules.append("unknown_localhost_proxy")

    ports = hc.allow_developer_proxy_ports
    for p in ports:
        if prox.endswith(f":{p}") or f":{p}" in prox:
            applied_rules.append("developer_proxy_allowlisted")

    if bundle.get("unsigned_path_hint"):
        applied_rules.append("unsigned_suspicious_path")

    if bundle.get("rollback_context"):
        if hc.rollback_requires_confirmation:
            applied_rules.append("rollback_confirmation_required")

    ctx = OperatorContext(role=operator_role, surface=surface)  # type: ignore[arg-type]
    sd = evaluate_structured(
        SignalSnapshot(summary=str(bundle.get("summary") or "")),
        remediation_action,
        ctx,
    )

    verb = _verb_from_structured(sd.execute_allowed, sd.preview_allowed, sd.reason_codes)

    if sd.risk_tier in {"high", "forbidden"} or "execute_blocked_high_or_forbidden_tier" in sd.reason_codes:
        applied_rules.append("high_risk_blocked")
        if verb != "block":
            verb = "block"

    return verb, {"structured": sd.model_dump(), "applied_rules": applied_rules}
