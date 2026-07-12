"""Localhost web-app diagnostics — ERR_CONNECTION_REFUSED / refused-to-connect evidence.

Module responsibility:
    Export diagnose and watch entry points for the Windows Network Toolkit CLI.

System placement:
    ``python -m windows_network_toolkit localhost-diagnose``
    ``python -m windows_network_toolkit localhost-watch``

Key invariants:
    * Read-only by default; remediation is preview-only.
    * Observation ≠ proof; CONNECTION_REFUSED ≠ firewall block.
"""

from .formatters import format_localhost_diagnose_human
from .runner import render_localhost_diagnose, run_localhost_diagnose
from .target import TargetValidationError, parse_localhost_target
from .watch import run_localhost_watch

__all__ = [
    "TargetValidationError",
    "format_localhost_diagnose_human",
    "parse_localhost_target",
    "render_localhost_diagnose",
    "run_localhost_diagnose",
    "run_localhost_watch",
]
