"""Post-repair verification by re-collecting evidence and comparing key signals."""

from __future__ import annotations

from typing import Callable

from .schemas import DiagnosticEvidence, VerificationResult


KeyFields = ("ping_ok", "dns_ok", "tcp_443_ok", "https_ok")


def verify_after_repair(
    evidence_before: DiagnosticEvidence,
    collector: Callable[[], DiagnosticEvidence],
) -> VerificationResult:
    """Re-run collection and compare primary booleans."""
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
    return {
        "passed": result.passed,
        "summary": result.summary,
        "evidence_after": result.evidence_after.to_dict(),
        "compared_fields": {k: {"before": v[0], "after": v[1]} for k, v in result.compared_fields.items()},
    }
