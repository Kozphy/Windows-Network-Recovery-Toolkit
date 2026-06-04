"""Normalize simulated edge-device telemetry into canonical signals and events.

Module responsibility:
    Convert a raw device-observation mapping (cpu_load, temperature_celsius, npu_available,
    inference_latency_ms, ...) into a deterministic canonical signal map plus a list of
    :class:`~platform_core.reasoning_models.EndpointEvent` rows for the edge reasoning engine.

System placement:
    First stage of :mod:`edge_device.reasoning`; analogous to
    ``platform_core.failure_scenarios.normalize_signals`` but for simulated embedded/AI-edge
    compute signals. Pure functions only — no hardware access, subprocess, or I/O.

Key invariants:
    * Thresholds are fixed constants (documented below) so the same observations always
      produce the same canonical signals and events (deterministic, replayable).
    * Missing raw fields degrade to ``None``/``False`` canonical signals; absence never
      raises and never fabricates a failure.

Input assumptions:
    ``raw`` is a flat ``dict`` of observation name -> value. Numeric fields may be int/float
    or numeric strings; booleans may be real bools or truthy strings.

Output guarantees:
    :func:`normalize_edge_signals` returns a ``dict`` of canonical signal -> value where
    derived booleans (``thermal_hot``, ``latency_regression``, ...) are real ``bool``.

Engineering Notes:
    Absolute thresholds (not learned baselines) keep the layer deterministic and testable
    offline. A ``baseline_latency_ms`` override is honored when supplied by a fixture so
    latency regression can be expressed relative to a per-device baseline without
    introducing nondeterminism.
"""

from __future__ import annotations

from typing import Any

from platform_core.reasoning_models import EndpointEvent, Observation

# Fixed, documented thresholds (deterministic; not calibrated probabilities).
CPU_HIGH = 0.85
MEMORY_PRESSURE_HIGH = 0.85
THERMAL_WARN_C = 75.0
THERMAL_HOT_C = 85.0
LATENCY_REGRESSION_MS = 120.0
LATENCY_BASELINE_MULTIPLIER = 2.5
INFERENCE_ERROR_HIGH = 0.05

_RAW_SIGNAL_NAMES = (
    "cpu_load",
    "memory_pressure",
    "temperature_celsius",
    "npu_available",
    "inference_latency_ms",
    "inference_error_rate",
    "driver_status",
    "sensor_input_status",
    "network_uplink_status",
)

_TRUTHY = {"true", "yes", "ok", "up", "available", "1", "online", "healthy"}


def _as_float(value: Any) -> float | None:
    """Coerce a numeric-or-string value to float, or ``None`` when not numeric."""
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_bool(value: Any) -> bool | None:
    """Coerce bool/str telemetry to bool; ``None`` when absent/unparseable."""
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in _TRUTHY:
        return True
    if text in {"false", "no", "down", "unavailable", "0", "offline"}:
        return False
    return None


def observations_from_raw(raw: dict[str, Any], *, source: str = "edge_fixture") -> list[Observation]:
    """Build :class:`Observation` rows for each recognized raw device signal.

    Args:
        raw: Flat device-observation mapping.
        source: Provenance label persisted on each observation (e.g. ``edge_fixture``).

    Returns:
        One :class:`Observation` per recognized signal present in ``raw`` (unknown keys
        are ignored, mirroring the platform engine's tolerance).
    """
    out: list[Observation] = []
    for name in _RAW_SIGNAL_NAMES:
        if name in raw:
            out.append(Observation(source=source, signal_name=name, value=raw[name]))
    return out


def normalize_edge_signals(raw: dict[str, Any]) -> dict[str, Any]:
    """Project raw device telemetry into the canonical edge signal map.

    Args:
        raw: Flat mapping of raw signal name -> value. Recognized keys are listed in
            :data:`_RAW_SIGNAL_NAMES`; an optional ``baseline_latency_ms`` tunes the
            latency-regression threshold relative to a per-device baseline.

    Returns:
        Canonical signal dict. Raw passthrough values plus derived booleans:
        ``cpu_high``, ``memory_pressure_high``, ``thermal_warn``, ``thermal_hot``,
        ``npu_available``, ``npu_unavailable``, ``latency_regression``,
        ``inference_error_high``, ``driver_mismatch``, ``sensor_degraded``,
        ``sensor_lost``, ``uplink_degraded``, ``uplink_down``, ``local_inference_ok``.

    Constraints:
        Deterministic for identical input. Missing fields yield ``False`` derived flags
        (never ``True``), so absence of evidence cannot manufacture a failure.
    """
    cpu = _as_float(raw.get("cpu_load"))
    mem = _as_float(raw.get("memory_pressure"))
    temp = _as_float(raw.get("temperature_celsius"))
    npu = _as_bool(raw.get("npu_available"))
    latency = _as_float(raw.get("inference_latency_ms"))
    err = _as_float(raw.get("inference_error_rate"))
    driver = str(raw.get("driver_status") or "").strip().lower() or None
    sensor = str(raw.get("sensor_input_status") or "").strip().lower() or None
    uplink = str(raw.get("network_uplink_status") or "").strip().lower() or None
    baseline = _as_float(raw.get("baseline_latency_ms"))

    latency_threshold = LATENCY_REGRESSION_MS
    if baseline is not None and baseline > 0:
        latency_threshold = min(LATENCY_REGRESSION_MS, baseline * LATENCY_BASELINE_MULTIPLIER)

    cpu_high = cpu is not None and cpu >= CPU_HIGH
    memory_pressure_high = mem is not None and mem >= MEMORY_PRESSURE_HIGH
    thermal_warn = temp is not None and temp >= THERMAL_WARN_C
    thermal_hot = temp is not None and temp >= THERMAL_HOT_C
    npu_unavailable = npu is False
    latency_regression = latency is not None and latency >= latency_threshold
    inference_error_high = err is not None and err >= INFERENCE_ERROR_HIGH
    driver_mismatch = driver is not None and driver not in {"ok", "match", "current"}
    sensor_degraded = sensor in {"degraded", "intermittent", "noisy"}
    sensor_lost = sensor in {"lost", "disconnected", "down"}
    uplink_degraded = uplink in {"degraded", "down", "offline", "lossy"}
    uplink_down = uplink in {"down", "offline"}

    # Local inference is "ok" when the device can still infer acceptably:
    # not erroring, not regressed on latency, and either NPU present or CPU fallback viable.
    local_inference_ok = (
        not inference_error_high
        and not latency_regression
        and not (sensor_lost)
        and (npu is not False or (cpu is not None and not cpu_high))
    )

    return {
        # raw passthrough (observed)
        "cpu_load": cpu,
        "memory_pressure": mem,
        "temperature_celsius": temp,
        "npu_available": bool(npu) if npu is not None else None,
        "inference_latency_ms": latency,
        "inference_error_rate": err,
        "driver_status": driver,
        "sensor_input_status": sensor,
        "network_uplink_status": uplink,
        # derived (inferred booleans)
        "cpu_high": cpu_high,
        "memory_pressure_high": memory_pressure_high,
        "thermal_warn": thermal_warn,
        "thermal_hot": thermal_hot,
        "npu_unavailable": npu_unavailable,
        "latency_regression": latency_regression,
        "inference_error_high": inference_error_high,
        "driver_mismatch": driver_mismatch,
        "sensor_degraded": sensor_degraded or sensor_lost,
        "sensor_lost": sensor_lost,
        "uplink_degraded": uplink_degraded,
        "uplink_down": uplink_down,
        "local_inference_ok": bool(local_inference_ok),
    }


# Map: canonical boolean signal -> emitted event type + severity.
_EVENT_RULES: tuple[tuple[str, str, str], ...] = (
    ("thermal_hot", "thermal_threshold_exceeded", "high"),
    ("thermal_warn", "thermal_warning", "medium"),
    ("cpu_high", "cpu_load_high", "medium"),
    ("memory_pressure_high", "memory_pressure_high", "medium"),
    ("npu_unavailable", "npu_unavailable", "high"),
    ("latency_regression", "inference_latency_regression", "high"),
    ("inference_error_high", "inference_error_elevated", "high"),
    ("driver_mismatch", "driver_runtime_mismatch", "high"),
    ("sensor_lost", "sensor_input_lost", "high"),
    ("sensor_degraded", "sensor_input_degraded", "medium"),
    ("uplink_down", "network_uplink_down", "medium"),
    ("uplink_degraded", "network_uplink_degraded", "low"),
)


def detect_edge_events(signals: dict[str, Any], observations: list[Observation]) -> list[EndpointEvent]:
    """Emit :class:`EndpointEvent` rows for each canonical signal that is true.

    Args:
        signals: Canonical map from :func:`normalize_edge_signals`.
        observations: Source observations (their ids are linked into each event).

    Returns:
        Ordered events (severity-significant first per :data:`_EVENT_RULES`). When no
        failure signal is set, a single ``edge_runtime_nominal`` info event is returned so
        the timeline always has an anchor.

    Side effects:
        None.
    """
    obs_ids = [o.id for o in observations]
    events: list[EndpointEvent] = []
    seen: set[str] = set()
    for signal_name, event_type, severity in _EVENT_RULES:
        if signals.get(signal_name) and event_type not in seen:
            seen.add(event_type)
            events.append(
                EndpointEvent(
                    source="edge_reasoning",
                    event_type=event_type,
                    severity=severity,  # type: ignore[arg-type]
                    status="observed",
                    observation_ids=obs_ids,
                    details={"signal": signal_name},
                )
            )
    if not events:
        events.append(
            EndpointEvent(
                source="edge_reasoning",
                event_type="edge_runtime_nominal",
                severity="info",
                status="observed",
                observation_ids=obs_ids,
                details={"signal": "nominal"},
            )
        )
    return events
