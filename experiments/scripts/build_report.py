#!/usr/bin/env python3
"""Regenerate benchmark tables and Markdown from raw case-level results."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.platform_core.evaluation.research_benchmark import run_cli  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(run_cli(["report", *sys.argv[1:]]))
