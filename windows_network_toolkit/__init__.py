"""Endpoint Reliability Decision Platform — portfolio-facing Windows toolkit facade.

Public surface:
    ``SERVICE_NAME`` and ``__version__`` for health endpoints and CLI banners.

System placement:
    Top-level package for ``python -m windows_network_toolkit`` CLI and FastAPI ERP routes.
    Implementation modules live alongside this file under ``windows_network_toolkit/``.

Positioning:
    Technology Risk & Control Analytics for endpoint proxy reliability — not antivirus,
    EDR, or autonomous remediation.
"""

from __future__ import annotations

__version__ = "0.2.0"
SERVICE_NAME = "endpoint-reliability-decision-platform"

__all__ = ["SERVICE_NAME", "__version__"]
