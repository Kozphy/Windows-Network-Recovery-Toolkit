"""Proxy Hijack & MITM Risk Detection Engine.

Local-first diagnostic package that inspects Windows proxy routing posture, correlates listener
process metadata, and emits explainable risk inference without automatic remediation.
"""

from .main import main

__all__ = ["main"]

