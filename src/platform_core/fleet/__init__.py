"""Fleet simulation and fixture-driven fleet summaries."""

from src.platform_core.fleet.simulator import (
    fleet_summary_from_fixture,
    load_fleet_fixture,
    render_fleet_markdown,
    replay_fleet_fixture,
)

__all__ = [
    "fleet_summary_from_fixture",
    "load_fleet_fixture",
    "render_fleet_markdown",
    "replay_fleet_fixture",
]
