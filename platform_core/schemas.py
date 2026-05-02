"""JSON export helpers for platform models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


def dump_model(model: BaseModel) -> dict[str, Any]:
    """Pydantic v2 compatible dict for API responses."""
    return model.model_dump()
