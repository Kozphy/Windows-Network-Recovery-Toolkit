"""Post-repair verification utilities for local repair workflows.

This module compares baseline and post-repair evidence to quantify improvement
without introducing additional remediation actions.
"""

from __future__ import annotations

from typing import Callable

from .schemas import DiagnosticEvidence, VerificationResult


KeyFields = ("ping_ok", "dns_ok", "tcp_443_ok", "https_ok")


def verify_after_repair(
    evidence_before: DiagnosticEvidence,
    collector: Callable[[], DiagnosticEvidence],
) -> VerificationResult:
    """Re-collect evidence and evaluate key connectivity signal deltas.

    Input assumptions:
        - `collector` returns a fresh `DiagnosticEvidence` snapshot.
        - Baseline evidence reflects pre-repair state.

    Output guarantees:
        - `compared_fields` includes all names in `KeyFields`.
        - `passed` is true when at least one improvement occurs with no
          regression, or when all key fields are true post-repair.

    Side effects:
        Depends on collector implementation (typically command execution).

    Idempotency:
        Deterministic for identical baseline and collector output.

    Args:
        evidence_before: Baseline evidence captured before repair attempt.
        collector: Callable that returns post-repair evidence.

    Returns:
        VerificationResult: Verification verdict with before/after details.
    """
    evidence_after = collector()
    compared: dict[str, tuple[object, object]] = {}
    improvements = 0
    regressions = 0
    for key in KeyFields:
        b = getattr(evidence_before, key)
        a = getattr(evidence_after, key)
        compared[key] = (b, a)
        if not b and a:
            improvements += 1
        if b and not a:
            regressions += 1

    passed = improvements >= 1 and regressions == 0
    if all(getattr(evidence_after, k) for k in KeyFields):
        passed = True

    summary_parts = [
        f"improvements={improvements}",
        f"regressions={regressions}",
    ]
    if passed:
        summary_parts.append("overall=PASS")
    else:
        summary_parts.append("overall=NEEDS_REVIEW")

    return VerificationResult(
        passed=passed,
        summary="; ".join(summary_parts),
        evidence_after=evidence_after,
        compared_fields=compared,
    )


def verification_to_dict(result: VerificationResult) -> dict[str, object]:
    """Serialize verification result into JSON-safe dictionary.

    Args:
        result: Verification result object.

    Returns:
        dict[str, object]: Dictionary representation for logging/reporting.
    """
    return {
        "passed": result.passed,
        "summary": result.summary,
        "evidence_after": result.evidence_after.to_dict(),
        "compared_fields": {k: {"before": v[0], "after": v[1]} for k, v in result.compared_fields.items()},
    }
