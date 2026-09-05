"""Deny-by-default registry for deterministic RiskClaw tools."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel

from riskclaw.schemas import ToolDefinition

ToolHandler = Callable[[BaseModel], Any]


class DuplicateToolError(ValueError):
    pass


class ToolNotFoundError(KeyError):
    pass


@dataclass(frozen=True)
class RegisteredTool:
    definition: ToolDefinition
    input_model: type[BaseModel]
    handler: ToolHandler


class ToolRegistry:
    """Register explicit handlers and validate inputs before any future execution layer."""

    def __init__(self) -> None:
        self._tools: dict[str, RegisteredTool] = {}

    def register(
        self,
        definition: ToolDefinition,
        *,
        input_model: type[BaseModel],
        handler: ToolHandler,
    ) -> RegisteredTool:
        if definition.name in self._tools:
            raise DuplicateToolError(f"tool already registered: {definition.name}")

        definition_with_schema = definition.model_copy(
            update={"input_schema": input_model.model_json_schema()}
        )
        registered = RegisteredTool(
            definition=definition_with_schema,
            input_model=input_model,
            handler=handler,
        )
        self._tools[definition.name] = registered
        return registered

    def get(self, name: str) -> RegisteredTool:
        try:
            return self._tools[name]
        except KeyError as exc:
            raise ToolNotFoundError(f"tool is not registered: {name}") from exc

    def validate_input(self, name: str, payload: dict[str, Any]) -> BaseModel:
        registered = self.get(name)
        return registered.input_model.model_validate(payload)

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._tools))

    def definitions(self) -> tuple[ToolDefinition, ...]:
        return tuple(self._tools[name].definition for name in self.names())
