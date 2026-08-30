"""Local monitoring dashboard package (NiceGUI, read-only).

Public exports: ``DashboardConfig``, ``create_runtime``, ``run_dashboard``.
Requires optional extras: ``pip install -e ".[dashboard]"``.
"""

from windows_network_toolkit.dashboard.app import create_runtime, run_dashboard
from windows_network_toolkit.dashboard.config import DashboardConfig

__all__ = ["DashboardConfig", "create_runtime", "run_dashboard"]
