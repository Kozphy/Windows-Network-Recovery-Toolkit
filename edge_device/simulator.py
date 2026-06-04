"""Deterministic simulated edge-device telemetry for ``--live-simulated`` runs.

Module responsibility:
    Produce reproducible raw observation mappings for the edge reasoning engine without any
    real hardware. A fixed seed yields identical telemetry so simulated runs stay replayable
    and testable.

System placement:
    Used by :mod:`edge_device.cli_handlers` for ``edge-diagnose --live-simulated``.

Key invariants:
    * Same ``seed`` + same ``profile`` -> identical observations (deterministic).
    * Values stay within plausible ranges; no network or device calls are made.

Engineering Notes:
    Profiles intentionally bias toward specific cataloged scenarios so the demo surfaces the
    full reasoning chain. This is simulation scaffolding, not a fidelity model of real
    silicon.
"""

from __future__ import annotations

import random
from typing import Any

SIM_PROFILES = ("nominal", "thermal", "npu_fallback", "latency", "driver", "sensor", "uplink")


def simulate_edge_observations(*, profile: str = "thermal", seed: int = 1729) -> dict[str, Any]:
    """Return a deterministic raw observation mapping for a named simulation profile.

    Args:
        profile: One of :data:`SIM_PROFILES`. Unknown profiles fall back to ``nominal``.
        seed: Deterministic seed; identical seed+profile yields identical output.

    Returns:
        Flat raw-observation dict consumable by
        :func:`edge_device.signals.normalize_edge_signals`.
    """
    rng = random.Random(f"{profile}:{seed}")

    def jitter(base: float, spread: float, ndigits: int = 3) -> float:
        return round(base + rng.uniform(-spread, spread), ndigits)

    obs: dict[str, Any] = {
        "cpu_load": jitter(0.45, 0.05),
        "memory_pressure": jitter(0.5, 0.05),
        "temperature_celsius": jitter(55.0, 2.0, 1),
        "npu_available": True,
        "inference_latency_ms": jitter(35.0, 5.0, 1),
        "inference_error_rate": jitter(0.01, 0.005, 4),
        "driver_status": "ok",
        "sensor_input_status": "ok",
        "network_uplink_status": "up",
    }

    if profile == "thermal":
        obs["temperature_celsius"] = jitter(89.0, 1.5, 1)
        obs["cpu_load"] = jitter(0.9, 0.03)
    elif profile == "npu_fallback":
        obs["npu_available"] = False
        obs["inference_latency_ms"] = jitter(160.0, 10.0, 1)
        obs["cpu_load"] = jitter(0.88, 0.03)
    elif profile == "latency":
        obs["inference_latency_ms"] = jitter(180.0, 15.0, 1)
        obs["memory_pressure"] = jitter(0.88, 0.02)
    elif profile == "driver":
        obs["driver_status"] = "version_mismatch"
        obs["npu_available"] = False
        obs["inference_error_rate"] = jitter(0.08, 0.01, 4)
    elif profile == "sensor":
        obs["sensor_input_status"] = "degraded"
        obs["inference_error_rate"] = jitter(0.07, 0.01, 4)
    elif profile == "uplink":
        obs["network_uplink_status"] = "degraded"
        # local inference stays healthy on purpose

    return obs


def simulated_device_profile(profile: str) -> dict[str, Any]:
    """Return descriptive (non-scoring) metadata for a simulated device profile."""
    return {
        "device_id": f"sim-edge-{profile}",
        "device_class": "x86_embedded_npu_simulated",
        "model": "simulated-ai-edge-soc",
        "simulation_profile": profile,
        "hardware_present": False,
    }
