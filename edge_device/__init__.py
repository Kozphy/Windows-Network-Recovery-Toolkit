"""Simulated AI-edge / embedded-compute reliability layer.

This package extends the local-first endpoint reliability toolkit toward AI-at-the-edge
and embedded-compute reliability (x86 embedded processors, NPUs, inference runtimes) using
**simulation and typed models only** — no real FPGA/NPU/hardware dependencies.

It follows the existing reasoning philosophy exactly:
observation -> event -> state transition -> ranked hypotheses -> evidence tree ->
optional (simulated) proof -> impact score -> policy (ALLOW/PREVIEW/BLOCK) -> append-only audit,
replayable without re-probing.

Public API:
    * :func:`edge_device.reasoning.run_edge_reasoning`
    * :func:`edge_device.policy.evaluate_edge_policy`
    * :class:`edge_device.models.EdgeReasoningRun`
    * :data:`edge_device.scenarios.EDGE_SCENARIOS`
    * :func:`edge_device.audit.append_edge_run` / :func:`edge_device.audit.load_edge_run`
"""

from edge_device.models import EdgeImpact, EdgeReasoningRun
from edge_device.policy import EDGE_SAFE_ACTIONS, evaluate_edge_policy
from edge_device.reasoning import run_edge_reasoning
from edge_device.scenarios import EDGE_SCENARIOS, rank_edge_hypotheses

__all__ = [
    "EDGE_SAFE_ACTIONS",
    "EDGE_SCENARIOS",
    "EdgeImpact",
    "EdgeReasoningRun",
    "evaluate_edge_policy",
    "rank_edge_hypotheses",
    "run_edge_reasoning",
]
