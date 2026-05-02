"""Read-only proxy detection helpers for corroborating Windows proxy symptoms.

Module responsibility:
    Re-exports :func:`proxy_attribution.attribution_engine.run_attribution`, the façade
    that wires collectors/classifiers together for ``python -m proxy_attribution``
    tooling.

System placement:
    Independent of ``src.proxy_guard`` (HKCU rollback pipeline) — share concepts only.

Key invariants:
    * Imports remain side-effect free; heavy Windows probes execute only inside CLI entry
      points documented in ``proxy_attribution/cli.py``.

Audit Notes:
    Outputs may reference hashed or redacted identifiers—treat classifier conclusions as
    diagnostic hints rather than attribution proof unless paired with authoritative logs.

See Also:
    Root ``README`` proxy CLI section and ``docs/proxy_guard.md`` for remediation paths.
"""

from __future__ import annotations

from proxy_attribution.attribution_engine import run_attribution

__all__ = ["run_attribution"]
__version__ = "0.1.0"
