"""Public package shim — implementation in ``src/trading_research/``."""

from __future__ import annotations

from pathlib import Path

_IMPL = Path(__file__).resolve().parent.parent / "src" / "trading_research"
__path__ = [str(_IMPL)]
VERSION = "0.1.0"
