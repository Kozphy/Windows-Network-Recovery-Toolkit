from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def knowledge_fixture_path() -> Path:
    root = Path(__file__).resolve().parents[2]
    path = root / "knowledge" / "endpoint_reliability.yaml"
    assert path.is_file(), f"missing {path}"
    return path


@pytest.fixture
def knowledge_dir() -> Path:
    root = Path(__file__).resolve().parents[2]
    path = root / "tests" / "fixtures" / "knowledge"
    assert path.is_dir(), f"missing {path}"
    return path
