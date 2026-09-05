"""Fixture-driven simulation — never mutates live Windows state."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.purple_team.models import ScenarioDefinition, TelemetryEvent
from src.purple_team.telemetry import make_event


def resolve_fixture_path(scenario: ScenarioDefinition, repo_root: Path) -> Path:
    raw = scenario.simulation.fixture_path
    path = Path(raw)
    if not path.is_absolute():
        path = repo_root / path
    return path


def load_fixture(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"fixture root must be object: {path}")
    return data


def simulate_from_fixture(
    scenario: ScenarioDefinition,
    *,
    run_id: str,
    repo_root: Path,
) -> tuple[dict[str, Any], list[TelemetryEvent]]:
    """Load fixture and emit normalized telemetry events (simulation stage)."""
    path = resolve_fixture_path(scenario, repo_root)
    fixture = load_fixture(path)
    events: list[TelemetryEvent] = []
    for raw in fixture.get("telemetry_events") or []:
        events.append(
            make_event(
                scenario_id=scenario.id,
                run_id=run_id,
                source=str(raw.get("source") or "fixture"),
                event_type=str(raw.get("event_type") or "configuration_change"),
                entity=str(raw.get("entity") or "unknown"),
                before=dict(raw.get("before") or {}),
                after=dict(raw.get("after") or {}),
                confidence=float(raw.get("confidence") or 0.98),
                host=str(fixture.get("host") or "fixture-host"),
                timestamp=raw.get("timestamp"),
            )
        )
    if not events:
        # Minimal synthetic event so pipeline can still classify absence.
        events.append(
            make_event(
                scenario_id=scenario.id,
                run_id=run_id,
                source="fixture",
                event_type="configuration_observation",
                entity=scenario.id,
                before=dict(fixture.get("pre_state") or {}),
                after=dict(fixture.get("post_state") or fixture.get("pre_state") or {}),
            )
        )
    return fixture, events
