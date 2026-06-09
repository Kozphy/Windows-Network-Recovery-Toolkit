"""Control mapping tests."""

from __future__ import annotations

from src.platform_core.governance.control_mapping import map_policy_outcome_to_controls


def test_block_maps_prevent() -> None:
    controls = map_policy_outcome_to_controls("BLOCK")
    assert "Prevent" in controls
    assert "Audit" in controls
