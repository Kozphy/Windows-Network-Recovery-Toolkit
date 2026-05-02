"""Toolkit decision pipelines (`FeatureVector`, scoring, Proxy Guard CLI wiring).

Package responsibility:
    Hosts collectors, deterministic root-cause scoring, tiered recommendation bundles,
    audit JSONL helpers, and the ``python -m src`` argument router implemented in
    ``src.cli``.

System placement:
    Primary advanced operator path beside ``failure_system`` (structured FailureBlocks)
    and optional ``endpoint_agent`` uploads. Shares repository ``scripts/*.bat``
    referrals but does not import those files.

Side effects:
    Importing this package is lightweight—it reads ``SCRIPT_VERSION`` from disk via
    ``src.version``. Running subcommands persists under ``reports/`` and ``logs/`` per
    command docstrings.

See Also:
    Root ``README`` advanced CLI section and ``docs/decision_engine_v2.md``.
"""

from .version import SCRIPT_VERSION

__all__ = ["SCRIPT_VERSION"]
