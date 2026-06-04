"""Edge failure-scenario catalog, hypothesis ranking, and evidence partitioning.

Module responsibility:
    Hold the closed catalog of edge/AI-compute failure hypotheses and rank them from the
    canonical signal map, then partition evidence into supporting / contradicting / missing
    for the accepted hypothesis.

System placement:
    Middle stage of :mod:`edge_device.reasoning`; analogous to
    ``platform_core.failure_scenarios`` for the proxy/browser engine.

Decision intent:
    Only hypotheses in :data:`EDGE_SCENARIOS` may ever be emitted. This is the guardrail
    against fabricated root causes: a signal pattern with no matching ``required`` set
    yields the nominal/indeterminate hypothesis, never an invented cause.

Key invariants:
    * Confidence is an ordinal rule-derived weight in ``[0.0, 0.95]`` — not a calibrated
      probability.
    * A hypothesis is a candidate only when **all** of its ``required`` signals are true.
    * Ranking is deterministic: score descending, ties broken by catalog order.

Inputs used for the decision:
    The canonical signal map from :func:`edge_device.signals.normalize_edge_signals`.

How to verify or audit:
    Re-run with the same signals; ranking and accepted hypothesis must match exactly.
    Each ranked row carries ``supporting``/``contradicting``/``missing`` signal names.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

NOMINAL_HYPOTHESIS = "edge_runtime_nominal"
INDETERMINATE_HYPOTHESIS = "edge_state_indeterminate"

# Confidence caps keep conclusions honest: unproven hypotheses never exceed CAP_UNPROVEN.
CAP_UNPROVEN = 0.9
CAP_CONFIRMED = 0.95
BASE_REQUIRED = 0.5
SUPPORT_WEIGHT = 0.12
CONTRADICT_WEIGHT = 0.2


@dataclass(frozen=True)
class EdgeScenario:
    """One edge failure hypothesis with its evidence contract.

    Attributes:
        id: Stable hypothesis identifier (must be one of the documented catalog ids).
        title: Human-readable summary for reports.
        required: Canonical signals that must **all** be true for candidacy.
        supporting: Signals that strengthen the hypothesis (additive ordinal weight).
        contradicting: Signals that weaken/should-exclude the hypothesis.
        proof_check: Name of the optional simulated proof check that could confirm it.
        safe_action: Allowlisted low-risk remediation action key suggested for PREVIEW.
    """

    id: str
    title: str
    required: tuple[str, ...]
    supporting: tuple[str, ...] = ()
    contradicting: tuple[str, ...] = ()
    proof_check: str = ""
    safe_action: str | None = None


EDGE_SCENARIOS: tuple[EdgeScenario, ...] = (
    EdgeScenario(
        id="thermal_throttling_risk",
        title="Thermal threshold exceeded; clock/inference throttling risk",
        required=("thermal_warn",),
        supporting=("thermal_hot", "cpu_high", "latency_regression"),
        proof_check="thermal_sensor_corroboration",
        safe_action="reduce_inference_load",
    ),
    EdgeScenario(
        id="driver_runtime_mismatch",
        title="NPU/accelerator driver or runtime version mismatch",
        required=("driver_mismatch",),
        supporting=("npu_unavailable", "inference_error_high"),
        proof_check="driver_runtime_version_contrast",
        safe_action="restart_inference_runtime",
    ),
    EdgeScenario(
        id="npu_fallback_to_cpu",
        title="NPU unavailable; inference fell back to CPU path",
        required=("npu_unavailable",),
        supporting=("latency_regression", "cpu_high"),
        contradicting=("driver_mismatch",),
        proof_check="npu_vs_cpu_inference_contrast",
        safe_action="switch_to_cpu_fallback",
    ),
    EdgeScenario(
        id="edge_inference_latency_regression",
        title="Inference latency regressed beyond threshold",
        required=("latency_regression",),
        supporting=("cpu_high", "memory_pressure_high", "npu_unavailable", "inference_error_high"),
        proof_check="inference_latency_contrast",
        safe_action="reduce_inference_load",
    ),
    EdgeScenario(
        id="sensor_input_degraded",
        title="Sensor input degraded or lost; inference quality at risk",
        required=("sensor_degraded",),
        supporting=("sensor_lost", "inference_error_high"),
        proof_check="sensor_signal_quality_contrast",
        safe_action="restart_inference_runtime",
    ),
    EdgeScenario(
        id="uplink_degraded_but_local_inference_ok",
        title="Network uplink degraded while local inference remains healthy",
        required=("uplink_degraded", "local_inference_ok"),
        supporting=("uplink_down",),
        contradicting=("inference_error_high", "latency_regression", "npu_unavailable"),
        proof_check="uplink_vs_local_inference_contrast",
        safe_action=None,
    ),
)

_BY_ID = {s.id: s for s in EDGE_SCENARIOS}


def scenario_by_id(hypothesis_id: str) -> EdgeScenario | None:
    """Return the catalog scenario for ``hypothesis_id`` or ``None`` when not cataloged."""
    return _BY_ID.get(hypothesis_id)


def _truthy(signals: dict[str, Any], name: str) -> bool:
    return bool(signals.get(name))


def _score(scenario: EdgeScenario, signals: dict[str, Any], *, proof_confirmed: bool) -> float:
    """Compute the ordinal confidence weight for a candidate scenario."""
    score = BASE_REQUIRED
    score += SUPPORT_WEIGHT * sum(1 for s in scenario.supporting if _truthy(signals, s))
    score -= CONTRADICT_WEIGHT * sum(1 for s in scenario.contradicting if _truthy(signals, s))
    cap = CAP_CONFIRMED if proof_confirmed else CAP_UNPROVEN
    return max(0.0, min(cap, round(score, 4)))


def rank_edge_hypotheses(
    signals: dict[str, Any],
    *,
    proof_hypothesis: str = "",
    proof_confirmed: bool = False,
) -> list[dict[str, Any]]:
    """Rank candidate edge hypotheses from the canonical signal map.

    Args:
        signals: Canonical signal map from :func:`edge_device.signals.normalize_edge_signals`.
        proof_hypothesis: Hypothesis id the optional proof check targeted (if any).
        proof_confirmed: ``True`` when that proof returned ``CONFIRMED`` (raises the cap and
            adds a small bonus to the matching hypothesis only).

    Returns:
        Ranked list (highest confidence first) of dicts with keys: ``hypothesis``,
        ``title``, ``confidence``, ``supporting``, ``contradicting``, ``missing``. When no
        scenario qualifies, a single nominal/indeterminate row is returned so callers never
        synthesize a non-cataloged cause.

    Constraints:
        Deterministic; only catalog hypotheses are ever returned.
    """
    rows: list[dict[str, Any]] = []
    for scenario in EDGE_SCENARIOS:
        if not all(_truthy(signals, r) for r in scenario.required):
            continue
        confirmed = proof_confirmed and proof_hypothesis == scenario.id
        confidence = _score(scenario, signals, proof_confirmed=confirmed)
        if confirmed:
            confidence = min(CAP_CONFIRMED, round(confidence + 0.05, 4))
        rows.append(
            {
                "hypothesis": scenario.id,
                "title": scenario.title,
                "confidence": confidence,
                "supporting": [s for s in (*scenario.required, *scenario.supporting) if _truthy(signals, s)],
                "contradicting": [s for s in scenario.contradicting if _truthy(signals, s)],
                "missing": [s for s in scenario.supporting if not _truthy(signals, s)],
            }
        )

    rows.sort(key=lambda r: float(r["confidence"]), reverse=True)
    if rows:
        return rows

    nominal = _looks_nominal(signals)
    return [
        {
            "hypothesis": NOMINAL_HYPOTHESIS if nominal else INDETERMINATE_HYPOTHESIS,
            "title": (
                "Edge runtime nominal; no cataloged failure pattern matched"
                if nominal
                else "Edge state indeterminate; insufficient signals to assert a cataloged cause"
            ),
            "confidence": 0.2 if nominal else 0.1,
            "supporting": [],
            "contradicting": [],
            "missing": [],
        }
    ]


def _looks_nominal(signals: dict[str, Any]) -> bool:
    """Return whether all known failure signals are absent (healthy device)."""
    failure_signals = (
        "cpu_high",
        "memory_pressure_high",
        "thermal_warn",
        "thermal_hot",
        "npu_unavailable",
        "latency_regression",
        "inference_error_high",
        "driver_mismatch",
        "sensor_degraded",
        "sensor_lost",
        "uplink_degraded",
    )
    return not any(_truthy(signals, s) for s in failure_signals)


def conflicting_edge_signals(signals: dict[str, Any]) -> bool:
    """Return whether directly contradictory edge signals are present.

    Mirrors the platform engine's conflict gate: contradictions reduce trust and force
    a PREVIEW outcome rather than ALLOW.
    """
    npu_conflict = bool(signals.get("npu_available")) and bool(signals.get("npu_unavailable"))
    health_conflict = bool(signals.get("local_inference_ok")) and bool(signals.get("inference_error_high"))
    uplink_conflict = bool(signals.get("uplink_down")) and (str(signals.get("network_uplink_status") or "") == "up")
    return npu_conflict or health_conflict or uplink_conflict
