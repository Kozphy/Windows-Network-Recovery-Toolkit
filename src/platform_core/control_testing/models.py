"""Control testing models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from src.platform_core.enterprise.enums import TestResult


class ControlTestExecution(BaseModel):
    test_id: str
    control_id: str
    control_name: str
    execution_time: str
    result: TestResult
    evidence: dict[str, Any] = Field(default_factory=dict)
    limitations: list[str] = Field(default_factory=list)
