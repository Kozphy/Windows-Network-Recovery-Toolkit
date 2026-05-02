"""Failure Knowledge System — deterministic probes, rules, FailureBlocks, and JSONL storage.

Module responsibility:
    Declares package version only; runtime entry points import submodules such as
    :mod:`failure_system.collector`, :mod:`failure_system.rules`, and :mod:`failure_system.api`.

System placement:
    Shared by ``python -m failure_system`` CLIs, optional FastAPI apps, and
    ``endpoint_agent.collect`` when those dependencies import successfully.

Key invariants:
    * Default posture is **diagnose + recommend text** without executing batch repairs from this
      package (see ``README`` / ``safety_model.md``).
    * JSONL roots honor ``FAILURE_SYSTEM_DATA_DIR`` when operators set it.

How other modules use it:
    ``endpoint_agent.collect`` imports collector/generator/rules for a single diagnostic cycle;
    the Endpoint Reliability Platform may consume derived ``FailureBlock`` identifiers separately.

See Also:
    ``docs/architecture.md`` and ``docs/failure_block_contract.md`` for contracts and diagrams.
"""

from __future__ import annotations

__version__ = "0.1.0"
