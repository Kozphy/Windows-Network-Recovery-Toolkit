"""Read-only proof verification facade."""

from __future__ import annotations

from typing import Any

from proxy_reasoning.models import ProxySignal
from proxy_reasoning.verification import run_verification_checks


def run_proof_checks(signals: dict[str, Any]) -> list[dict[str, Any]]:
    """Run proxy_reasoning verification against a signal dict."""
    proxy_signals = [ProxySignal(name=k, value=v) for k, v in signals.items()]
    results = run_verification_checks(proxy_signals)
    out: list[dict[str, Any]] = []
    for r in results:
        out.append(
            {
                "check_id": getattr(r, "check_id", ""),
                "status": getattr(r, "status", ""),
                "detail": getattr(r, "detail", ""),
            }
        )
    return out
