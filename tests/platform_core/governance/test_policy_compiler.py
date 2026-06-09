"""Policy compiler tests."""

from __future__ import annotations

from pathlib import Path

from src.platform_core.governance.policy_compiler import compile_policy_matrix

_REPO = Path(__file__).resolve().parents[3]


def test_compile_default_policy() -> None:
    result = compile_policy_matrix(_REPO / "src" / "policy" / "default_policy.yaml")
    assert result["status"] in {"compiled", "missing"}
