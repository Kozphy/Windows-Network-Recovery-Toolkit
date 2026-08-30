"""Governed AI-agent orchestration for evidence-based investigations.

The agent layer may explain and recommend, but it cannot authorize execution.
"""

from .orchestrator import GovernedInvestigation, InvestigationResult

__all__ = ["GovernedInvestigation", "InvestigationResult"]
