"""Scenario schema load/validate — incomplete safety/rollback is rejected."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from src.purple_team.models import (
    MitreMapping,
    ScenarioCleanup,
    ScenarioDefinition,
    ScenarioSimulation,
    ScenarioVerification,
)

REQUIRED_TOP = (
    "id",
    "title",
    "category",
    "risk_level",
    "safe_for_local_execution",
    "preconditions",
    "simulation",
    "expected_telemetry",
    "expected_detection",
    "expected_response",
    "verification",
    "cleanup",
)


class ScenarioSchemaError(ValueError):
    """Raised when a scenario definition is incomplete or unsafe-by-omission."""


def _require(data: dict[str, Any], key: str, ctx: str) -> Any:
    if key not in data:
        raise ScenarioSchemaError(f"{ctx}: missing required field '{key}'")
    return data[key]


def validate_raw_scenario(data: dict[str, Any]) -> ScenarioDefinition:
    """Validate and construct a ScenarioDefinition from a mapping."""
    for key in REQUIRED_TOP:
        _require(data, key, "scenario")

    if not isinstance(data["preconditions"], list) or not data["preconditions"]:
        raise ScenarioSchemaError("scenario.preconditions must be a non-empty list")

    sim = data["simulation"]
    if not isinstance(sim, dict):
        raise ScenarioSchemaError("scenario.simulation must be an object")
    for key in ("action", "fixture_path"):
        _require(sim, key, "simulation")

    ver = data["verification"]
    if not isinstance(ver, dict):
        raise ScenarioSchemaError("scenario.verification must be an object")
    pcs = _require(ver, "post_conditions", "verification")
    if not isinstance(pcs, list) or not pcs:
        raise ScenarioSchemaError("verification.post_conditions must be non-empty")

    cleanup = data["cleanup"]
    if not isinstance(cleanup, dict):
        raise ScenarioSchemaError("scenario.cleanup must be an object")
    if "required" not in cleanup:
        raise ScenarioSchemaError("cleanup.required is mandatory")
    if cleanup["required"] is not True:
        raise ScenarioSchemaError(
            "cleanup.required must be true — scenarios without rollback are rejected"
        )
    steps = cleanup.get("steps") or []
    if not isinstance(steps, list) or not steps:
        raise ScenarioSchemaError("cleanup.steps must be a non-empty list when required")

    if data.get("allows_remote_target") is True:
        raise ScenarioSchemaError("remote targets are forbidden in purple scenarios")
    if data.get("allows_production_target") is True:
        raise ScenarioSchemaError("production targets are forbidden in purple scenarios")

    if not data["safe_for_local_execution"]:
        raise ScenarioSchemaError(
            "safe_for_local_execution must be true for loadable scenarios"
        )

    mitre_raw = data.get("mitre") or {}
    techniques = tuple(mitre_raw.get("techniques") or ())
    for tid in techniques:
        if not isinstance(tid, str) or not tid.startswith("T"):
            raise ScenarioSchemaError(f"invalid MITRE technique id: {tid!r}")

    return ScenarioDefinition(
        id=str(data["id"]),
        title=str(data["title"]),
        category=str(data["category"]),
        risk_level=str(data["risk_level"]),
        safe_for_local_execution=bool(data["safe_for_local_execution"]),
        preconditions=tuple(str(x) for x in data["preconditions"]),
        simulation=ScenarioSimulation(
            action=str(sim["action"]),
            fixture_path=str(sim["fixture_path"]),
            produces_events=tuple(sim.get("produces_events") or []),
            notes=str(sim.get("notes") or ""),
        ),
        expected_telemetry=tuple(str(x) for x in data["expected_telemetry"]),
        expected_detection=str(data["expected_detection"]),
        expected_response=str(data["expected_response"]),
        verification=ScenarioVerification(
            post_conditions=tuple(str(x) for x in pcs),
            independent=bool(ver.get("independent", True)),
        ),
        cleanup=ScenarioCleanup(required=True, steps=tuple(str(x) for x in steps)),
        expect_detection=bool(data.get("expect_detection", True)),
        benign_control=bool(data.get("benign_control", False)),
        authorized_execution_required=bool(
            data.get("authorized_execution_required", True)
        ),
        allows_remote_target=False,
        allows_production_target=False,
        mitre=MitreMapping(
            techniques=techniques,
            notes=str(mitre_raw.get("notes") or ""),
        ),
        description=str(data.get("description") or ""),
        false_positive_notes=str(data.get("false_positive_notes") or ""),
        limitations=tuple(str(x) for x in (data.get("limitations") or [])),
    )


def load_scenario_file(path: Path) -> ScenarioDefinition:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in {".yaml", ".yml"}:
        data = yaml.safe_load(text)
    else:
        data = json.loads(text)
    if not isinstance(data, dict):
        raise ScenarioSchemaError(f"{path}: root must be a mapping")
    return validate_raw_scenario(data)


def default_scenarios_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "scenarios"


def list_scenario_files(directory: Path | None = None) -> list[Path]:
    root = directory or default_scenarios_dir()
    if not root.is_dir():
        return []
    files = sorted(root.glob("*.yaml")) + sorted(root.glob("*.yml")) + sorted(root.glob("*.json"))
    # de-dupe while preserving order
    seen: set[Path] = set()
    out: list[Path] = []
    for p in files:
        if p not in seen:
            seen.add(p)
            out.append(p)
    return out


def load_all_scenarios(directory: Path | None = None) -> list[ScenarioDefinition]:
    return [load_scenario_file(p) for p in list_scenario_files(directory)]
