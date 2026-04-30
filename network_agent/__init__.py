"""Core package for the Hybrid AI Network Diagnostic Agent.

This package groups ingestion (collectors), deterministic diagnosis (engine),
safety policy, reporting, and serving entrypoints (CLI/API).

System placement:
    Windows probes -> decision rules -> report persistence -> API/UI delivery.

Key invariants:
    - Diagnosis logic is deterministic and explainable.
    - Repair paths are policy-gated and confirmation-driven.
    - Firewall reset is never auto-executed by package defaults.
"""

from .engine.decision_engine import diagnose

__all__ = ["diagnose"]
