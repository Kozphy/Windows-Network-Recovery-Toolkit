"""Business objective models for technology risk decisions."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class BusinessObjective(BaseModel):
    objective_id: str
    name: str
    description: str
    owner: str = "IT Operations"
    priority: str = "high"


def objective_for_fixture(fixture: dict[str, Any]) -> BusinessObjective:
    override = fixture.get("business_objective")
    if override:
        return BusinessObjective.model_validate(override)
    return BusinessObjective(
        objective_id="OBJ_BROWSER_ACCESS",
        name="Maintain reliable and secure browser/network access",
        description=(
            "Ensure corporate endpoints can reach business web applications "
            "without misconfigured proxy state or unaudited configuration drift."
        ),
        owner="IT Operations / Endpoint Engineering",
        priority="high",
    )
