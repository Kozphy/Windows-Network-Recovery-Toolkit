"""Fleet simulation CLI — fixture-safe JSON and Markdown output."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from src.platform_core.fleet.simulator import (
    fleet_summary_from_fixture,
    render_fleet_markdown,
)


def run_fleet_simulate(
    *,
    fixture: str,
    fmt: str = "json",
) -> dict[str, Any] | str:
    summary = fleet_summary_from_fixture(fixture)
    if fmt == "markdown":
        return render_fleet_markdown(summary)
    return summary


def cmd_fleet_simulate(args) -> int:
    fixture = args.fixture
    if not Path(fixture).is_file():
        repo = Path(__file__).resolve().parents[1]
        alt = repo / fixture
        if alt.is_file():
            fixture = str(alt)
        else:
            print(f"Fixture not found: {args.fixture}", file=sys.stderr)
            return 1
    fmt = getattr(args, "format", "json") or "json"
    if fmt == "markdown":
        text = run_fleet_simulate(fixture=fixture, fmt="markdown")
        print(text)
    else:
        payload = run_fleet_simulate(fixture=fixture, fmt="json")
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0
