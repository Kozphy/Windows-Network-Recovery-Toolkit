"""DEPRECATED: use ``src.platform.serialization``."""

from __future__ import annotations

import warnings

from pydantic import BaseModel

from src.platform.serialization import canonical_json, content_hash

warnings.warn("src.core.serialization is deprecated; use src.platform.serialization", DeprecationWarning, stacklevel=2)


def json_schema(model: type[BaseModel]) -> dict:
    return model.model_json_schema()


__all__ = ["canonical_json", "content_hash", "json_schema"]
