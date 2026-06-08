from __future__ import annotations

from pathlib import Path

import pytest

from platform_core.outcome_learning import DecisionOutcome, load_outcomes


@pytest.fixture
def outcomes_fixture_path() -> Path:
    root = Path(__file__).resolve().parents[2]
    path = root / "fixtures" / "outcome_learning" / "outcomes.json"
    assert path.is_file(), f"missing {path}"
    return path


@pytest.fixture
def sample_outcomes(outcomes_fixture_path: Path) -> list[DecisionOutcome]:
    return load_outcomes(outcomes_fixture_path)
