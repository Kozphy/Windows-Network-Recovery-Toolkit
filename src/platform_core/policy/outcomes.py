"""Policy outcome vocabulary."""

from __future__ import annotations

from typing import Literal

PolicyOutcomeName = Literal[
    "ALLOW",
    "PREVIEW_ONLY",
    "REQUIRE_HUMAN_APPROVAL",
    "BLOCK",
    "ROLLBACK_REQUIRED",
]
