"""Typed tool registry tests."""

from __future__ import annotations

import pytest
from pydantic import BaseModel, ConfigDict, ValidationError

from riskclaw.schemas import ToolDefinition, ToolRiskClass
from riskclaw.tools import DuplicateToolError, ToolNotFoundError, ToolRegistry


class ProxyCollectInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    endpoint_id: str


def _handler(payload: BaseModel) -> dict[str, str]:
    typed = ProxyCollectInput.model_validate(payload)
    return {"endpoint_id": typed.endpoint_id}


def _definition() -> ToolDefinition:
    return ToolDefinition(
        name="proxy.collect",
        description="Collect deterministic proxy state evidence.",
        risk_class=ToolRiskClass.READ_ONLY,
        limitations=["Collector output is observation, not proof."],
    )


def test_register_populates_json_schema_and_validates_input() -> None:
    registry = ToolRegistry()
    registered = registry.register(
        _definition(),
        input_model=ProxyCollectInput,
        handler=_handler,
    )

    payload = registry.validate_input("proxy.collect", {"endpoint_id": "ep-1"})

    assert registered.definition.input_schema["type"] == "object"
    assert payload.endpoint_id == "ep-1"
    assert registry.names() == ("proxy.collect",)


def test_duplicate_tool_registration_is_rejected() -> None:
    registry = ToolRegistry()
    registry.register(_definition(), input_model=ProxyCollectInput, handler=_handler)

    with pytest.raises(DuplicateToolError):
        registry.register(_definition(), input_model=ProxyCollectInput, handler=_handler)


def test_unknown_tool_fails_closed() -> None:
    with pytest.raises(ToolNotFoundError):
        ToolRegistry().get("shell.execute")


def test_tool_input_rejects_unknown_fields() -> None:
    registry = ToolRegistry()
    registry.register(_definition(), input_model=ProxyCollectInput, handler=_handler)

    with pytest.raises(ValidationError):
        registry.validate_input(
            "proxy.collect",
            {"endpoint_id": "ep-1", "command": "arbitrary shell"},
        )
